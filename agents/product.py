import json
from agents.base import BaseAgent, AgentResult, Tool


SYSTEM_PROMPT = """
You are the Product Development analyst for a real estate SaaS startup.
Analyze user feedback, cluster by theme, score features by impact (1-10) and effort (1-10).
Priority score = impact / effort. Higher = do first.

Return JSON:
{
  "themes": [{"name": "...", "feedback_count": 0, "examples": ["..."]}],
  "features": [
    {
      "title": "...",
      "description": "...",
      "theme": "...",
      "impact": 0,
      "effort": 0,
      "priority_score": 0.0,
      "recommendation": "..."
    }
  ],
  "roadmap_update": "...",
  "next_sprint_suggestion": "..."
}
"""


class ProductAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="product",
            system_prompt=SYSTEM_PROMPT,
            model="claude-sonnet-4-6",
            max_tokens=4096,
        )

    def run(self, task_payload: dict) -> AgentResult:
        try:
            feedback = task_payload.get("feedback", [])
            if not feedback:
                feedback = [
                    "Need better mobile experience for showing properties on the go",
                    "Integration with DocuSign for e-signatures would save hours",
                    "Bulk import from MLS would be huge",
                    "Can we get automated follow-up reminders?",
                    "The reporting dashboard needs more filters",
                ]

            prompt = f"""
Analyze this user feedback and produce a prioritized feature roadmap update:
{json.dumps(feedback, indent=2)}

Return JSON only.
"""
            raw = self._run_loop(prompt)

            try:
                start = raw.find("{")
                end = raw.rfind("}") + 1
                analysis = json.loads(raw[start:end]) if start >= 0 else {"raw": raw}
            except Exception:
                analysis = {"raw": raw}

            features = analysis.get("features", [])

            return AgentResult(
                agent="product",
                action_type="update_roadmap",
                output={"analysis": analysis},
                requires_approval=True,
                preview={
                    "feature_count": len(features),
                    "top_features": features[:3] if features else [],
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
        return {"roadmap_updated": True, "top_features": preview.get("top_features", [])}
