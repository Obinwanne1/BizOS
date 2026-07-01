import json
import os
import logging
from dataclasses import dataclass, field
from typing import Callable, Generator
import anthropic
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 10


def _memory_read(agent: str, memory_type: str = None, limit: int = 10) -> dict:
    from orchestrator.state import get_memories
    memories = get_memories(agent, memory_type=memory_type or None, limit=limit)
    return {"memories": memories, "count": len(memories)}


def _memory_write(agent: str, memory_type: str, key: str, value: str, confidence: float = 1.0) -> dict:
    from orchestrator.state import save_memory
    memory_id = save_memory(agent, memory_type, key, value, confidence=confidence, source="agent")
    return {"saved": True, "id": memory_id, "key": key}


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
        self._on_chunk: Callable[[str], None] | None = None
        self._register_tools()
        self._attach_memory_tools()

    def _register_tools(self):
        pass

    def _attach_memory_tools(self):
        agent_name = self.name
        self._tools += [
            Tool(
                name="read_memory",
                description="Read memories saved by this agent from previous runs. Use at start of task to recall past outcomes, preferences, and context.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "memory_type": {
                            "type": "string",
                            "description": "Filter by type: fact, outcome, preference, lead_context, campaign, roadmap. Omit for all.",
                        },
                        "limit": {"type": "integer", "description": "Max memories to return (default 10)"},
                    },
                    "required": [],
                },
                handler=lambda memory_type=None, limit=10: _memory_read(agent_name, memory_type, limit),
            ),
            Tool(
                name="write_memory",
                description="Save a memory for use in future runs. Use to persist what worked, what to avoid, key outcomes, and learned preferences.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "memory_type": {
                            "type": "string",
                            "description": "Type: fact, outcome, preference, lead_context, campaign, roadmap",
                        },
                        "key": {"type": "string", "description": "Short identifier for this memory (e.g. 'best_linkedin_hook')"},
                        "value": {"type": "string", "description": "The memory content to store"},
                        "confidence": {"type": "number", "description": "How confident you are (0.0-1.0, default 1.0)"},
                    },
                    "required": ["memory_type", "key", "value"],
                },
                handler=lambda memory_type, key, value, confidence=1.0: _memory_write(agent_name, memory_type, key, value, confidence),
            ),
        ]

    def _get_memory_context(self) -> str:
        try:
            from orchestrator.state import get_memories
            memories = get_memories(self.name, limit=10)
            if not memories:
                return ""
            lines = ["[Memories from previous runs — use these to inform your work:]"]
            for m in memories:
                lines.append(f"- [{m['memory_type']}] {m['key']}: {m['value']}")
            return "\n".join(lines) + "\n\n"
        except Exception:
            return ""

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
        if self._on_chunk is not None:
            return self._run_loop_streaming(user_message)

        memory_ctx = self._get_memory_context()
        if memory_ctx:
            user_message = memory_ctx + user_message
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

    def _run_loop_streaming(self, user_message: str) -> str:
        """Streaming variant — calls self._on_chunk(delta) for every text token.
        Returns accumulated full text. Only called when self._on_chunk is set."""
        memory_ctx = self._get_memory_context()
        if memory_ctx:
            user_message = memory_ctx + user_message
        messages = [{"role": "user", "content": user_message}]
        tool_map = self._tool_map()
        accumulated: list[str] = []
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
                with self.client.messages.stream(**kwargs) as stream:
                    for delta in stream.text_stream:
                        accumulated.append(delta)
                        if self._on_chunk:
                            self._on_chunk(delta)
                    final = stream.get_final_message()
            except anthropic.APIStatusError as e:
                logger.error("[%s] Anthropic API error (stream): %s", self.name, e)
                raise

            if final.stop_reason in ("end_turn", "max_tokens"):
                if final.stop_reason == "max_tokens":
                    logger.warning("[%s] Hit max_tokens in streaming mode.", self.name)
                break

            if final.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": final.content})
                tool_results = []
                tool_names = []
                for block in final.content:
                    if block.type == "tool_use":
                        tool_names.append(block.name)
                        handler = tool_map.get(block.name)
                        if handler:
                            try:
                                result = handler(**block.input)
                            except Exception as e:
                                logger.error("[%s] Tool %s failed: %s", self.name, block.name, e)
                                result = {"error": str(e)}
                        else:
                            result = {"error": f"Unknown tool: {block.name}"}
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        })
                # Emit tool indicator so UI shows agent is working
                if tool_names and self._on_chunk:
                    indicator = f"\n\n*[{', '.join(tool_names)}...]*\n\n"
                    accumulated.append(indicator)
                    self._on_chunk(indicator)
                messages.append({"role": "user", "content": tool_results})
                continue

            logger.warning("[%s] Unexpected stop_reason in stream: %s", self.name, final.stop_reason)
            break

        if iterations >= MAX_TOOL_ITERATIONS:
            logger.error("[%s] Hit MAX_TOOL_ITERATIONS in streaming mode.", self.name)

        return "".join(accumulated)

    def run(self, task_payload: dict) -> AgentResult:
        raise NotImplementedError
