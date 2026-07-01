from agents.base import BaseAgent, AgentResult, Tool
from tools.web_research import search_re_news
from utils.json_parser import extract_json
from utils.config_loader import get_model, get_max_tokens

SYSTEM_PROMPT = """
You are the Marketing strategist for a real estate SaaS startup.
Analyze performance context and recommend campaigns. Be ROI-focused and evidence-based.
Ground recommendations in current RE industry trends — use get_industry_trends first.

Return raw JSON only (no markdown fences):
{
  "weekly_summary": "2-3 sentence summary of the week",
  "top_performing": ["content or channel that worked"],
  "underperforming": ["what to cut or rethink"],
  "recommendations": [
    {
      "campaign": "campaign name",
      "channel": "LinkedIn|Email|Twitter|Instagram",
      "rationale": "why this will work for RE pros",
      "estimated_impact": "qualitative or quantitative estimate"
    }
  ],
  "next_week_focus": "one clear priority"
}
"""


class MarketingAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="marketing",
            system_prompt=SYSTEM_PROMPT,
            model=get_model("marketing"),
            max_tokens=get_max_tokens("marketing"),
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
            context = task_payload.get("context", "Generate this week's marketing strategy for a real estate SaaS")
            prompt = (
                f"{context}\n"
                "Use get_industry_trends to ground recommendations in current market conditions.\n"
                "Return raw JSON only."
            )
            raw = self._run_loop(prompt)
            strategy = extract_json(raw, expect="object")

            if not strategy.get("recommendations"):
                strategy = {"weekly_summary": raw, "recommendations": [], "next_week_focus": ""}

            return AgentResult(
                agent="marketing",
                action_type="marketing_strategy",
                output={"strategy": strategy},
                requires_approval=True,
                preview={
                    "summary": strategy.get("weekly_summary", ""),
                    "top_performing": strategy.get("top_performing", []),
                    "underperforming": strategy.get("underperforming", []),
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
        from tools.google_workspace import write_to_sheets
        result = write_to_sheets(
            title=f"Marketing Strategy",
            data=preview,
        )
        return {
            "logged": True,
            "recommendation_count": len(preview.get("recommendations", [])),
            "focus": preview.get("next_week_focus", ""),
            "sheets_result": result,
        }
