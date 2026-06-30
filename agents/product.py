import json
from agents.base import BaseAgent, AgentResult
from utils.json_parser import extract_json
from utils.config_loader import get_model, get_max_tokens

SYSTEM_PROMPT = """
You are the Product Development analyst for a real estate SaaS startup.
Analyze user feedback, cluster by theme, score features by impact (1-10) and effort (1-10).
Priority score = impact / effort — higher means do it sooner.
Think like a PM: be opinionated, make a call, don't hedge.

Return raw JSON only (no markdown fences):
{
  "themes": [{"name": "...", "feedback_count": 0, "examples": ["..."]}],
  "features": [
    {
      "title": "...",
      "description": "...",
      "theme": "...",
      "impact": 8,
      "effort": 3,
      "priority_score": 2.67,
      "recommendation": "Ship in next sprint|Backlog|Needs more research|Won't do"
    }
  ],
  "roadmap_update": "narrative summary of what changed and why",
  "next_sprint_suggestion": "one specific sprint goal"
}
"""

DEFAULT_FEEDBACK = [
    "Need better mobile experience for showing properties on the go",
    "Integration with DocuSign for e-signatures would save hours per deal",
    "Bulk import from MLS would be huge — I have 200 listings to import",
    "Automated follow-up reminders when a lead goes cold",
    "The reporting dashboard needs more filters — city, price range, agent",
]


class ProductAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="product",
            system_prompt=SYSTEM_PROMPT,
            model=get_model("product"),
            max_tokens=get_max_tokens("product"),
        )

    def run(self, task_payload: dict) -> AgentResult:
        try:
            feedback = task_payload.get("feedback") or DEFAULT_FEEDBACK
            if not isinstance(feedback, list):
                feedback = [str(feedback)]

            prompt = (
                f"Analyze this user feedback and produce a prioritized roadmap update:\n"
                f"{json.dumps(feedback, indent=2)}\n\n"
                "Return raw JSON only."
            )
            raw = self._run_loop(prompt)
            analysis = extract_json(raw, expect="object")

            if not analysis.get("features"):
                analysis = {"roadmap_update": raw, "features": [], "themes": [], "next_sprint_suggestion": ""}

            features = analysis.get("features", [])
            sorted_features = sorted(features, key=lambda f: f.get("priority_score", 0), reverse=True)

            return AgentResult(
                agent="product",
                action_type="update_roadmap",
                output={"analysis": analysis},
                requires_approval=True,
                preview={
                    "feature_count": len(sorted_features),
                    "top_features": sorted_features[:3],
                    "themes": analysis.get("themes", []),
                    "roadmap_update": analysis.get("roadmap_update", ""),
                    "next_sprint": analysis.get("next_sprint_suggestion", ""),
                    "action": "Write roadmap update to Google Drive",
                },
            )
        except Exception as e:
            return AgentResult(
                agent="product",
                action_type="update_roadmap",
                output={},
                requires_approval=False,
                error=str(e),
            )

    def execute_approved(self, action_type: str, preview: dict) -> dict:
        return {
            "roadmap_updated": True,
            "top_features": preview.get("top_features", []),
            "next_sprint": preview.get("next_sprint", ""),
        }
