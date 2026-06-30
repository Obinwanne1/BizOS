import json
from agents.base import BaseAgent, AgentResult, Tool
from tools.web_research import search_re_news


SYSTEM_PROMPT = """
You are the Marketing strategist for a real estate SaaS startup.
Analyze performance data and recommend campaigns. Be ROI-focused and evidence-based.

Return JSON:
{
  "weekly_summary": "...",
  "top_performing": ["..."],
  "underperforming": ["..."],
  "recommendations": [
    {"campaign": "...", "channel": "...", "rationale": "...", "estimated_impact": "..."}
  ],
  "next_week_focus": "..."
}
"""


class MarketingAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="marketing",
            system_prompt=SYSTEM_PROMPT,
            model="claude-sonnet-4-6",
            max_tokens=4096,
        )

    def _register_tools(self):
        self._tools = [
            Tool(
                name="get_industry_trends",
                description="Get current RE industry trends to inform campaign strategy",
                input_schema={
                    "type": "object",
                    "properties": {"topic": {"type": "string"}},
                    "required": [],
                },
                handler=lambda topic="real estate marketing trends": search_re_news(topic),
            ),
        ]

    def run(self, task_payload: dict) -> AgentResult:
        try:
            context = task_payload.get("context", "Generate weekly marketing strategy")
            raw = self._run_loop(f"{context}\nReturn JSON only.")

            try:
                start = raw.find("{")
                end = raw.rfind("}") + 1
                strategy = json.loads(raw[start:end]) if start >= 0 else {"raw": raw}
            except Exception:
                strategy = {"raw": raw}

            return AgentResult(
                agent="marketing",
                action_type="marketing_strategy",
                output={"strategy": strategy},
                requires_approval=True,
                preview={
                    "summary": strategy.get("weekly_summary", ""),
                    "recommendations": strategy.get("recommendations", []),
                    "next_week_focus": strategy.get("next_week_focus", ""),
                    "action": "Log strategy to Google Sheets",
                },
            )
        except Exception as e:
            return AgentResult(
                agent="marketing",
                action_type="marketing_strategy",
                output={},
                requires_approval=False,
                error=str(e),
            )

    def execute_approved(self, action_type: str, preview: dict) -> dict:
        return {"logged": True, "recommendations": len(preview.get("recommendations", []))}
