import json
import os
import logging
from dataclasses import dataclass, field
from typing import Callable
import anthropic
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 10


@dataclass
class AgentResult:
    agent: str
    action_type: str
    output: dict
    requires_approval: bool
    preview: dict = field(default_factory=dict)
    error: str = ""

    @property
    def success(self) -> bool:
        return not self.error


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    handler: Callable


class BaseAgent:
    def __init__(self, name: str, system_prompt: str, model: str, max_tokens: int = 4096):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY not set in environment")

        self.name = name
        self.system_prompt = system_prompt
        self.model = model
        self.max_tokens = max_tokens
        self.client = anthropic.Anthropic(api_key=api_key)
        self._tools: list[Tool] = []
        self._register_tools()

    def _register_tools(self):
        pass

    def _tool_defs(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in self._tools
        ]

    def _tool_map(self) -> dict[str, Callable]:
        return {t.name: t.handler for t in self._tools}

    def _run_loop(self, user_message: str) -> str:
        messages = [{"role": "user", "content": user_message}]
        tool_map = self._tool_map()
        iterations = 0

        while iterations < MAX_TOOL_ITERATIONS:
            iterations += 1
            kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "system": self.system_prompt,
                "messages": messages,
            }
            if self._tools:
                kwargs["tools"] = self._tool_defs()

            try:
                response = self.client.messages.create(**kwargs)
            except anthropic.APIStatusError as e:
                logger.error("[%s] Anthropic API error: %s", self.name, e)
                raise

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        return block.text
                return ""

            if response.stop_reason == "max_tokens":
                logger.warning("[%s] Hit max_tokens limit (%d). Returning partial output.", self.name, self.max_tokens)
                for block in response.content:
                    if hasattr(block, "text"):
                        return block.text
                return ""

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        handler = tool_map.get(block.name)
                        if handler:
                            try:
                                result = handler(**block.input)
                            except Exception as e:
                                logger.error("[%s] Tool %s failed: %s", self.name, block.name, e)
                                result = {"error": str(e)}
                        else:
                            result = {"error": f"Unknown tool: {block.name}"}
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps(result),
                            }
                        )
                messages.append({"role": "user", "content": tool_results})
                continue

            logger.warning("[%s] Unexpected stop_reason: %s", self.name, response.stop_reason)
            break

        if iterations >= MAX_TOOL_ITERATIONS:
            logger.error("[%s] Hit MAX_TOOL_ITERATIONS (%d). Aborting loop.", self.name, MAX_TOOL_ITERATIONS)

        return ""

    def run(self, task_payload: dict) -> AgentResult:
        raise NotImplementedError
