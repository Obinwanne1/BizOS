import json
from datetime import datetime
from agents.base import BaseAgent, AgentResult, Tool
from orchestrator.state import get_pending_approvals, get_agent_logs, get_stats
from tools.slack_notifier import send_slack_message
from tools.google_workspace import get_calendar_today
from utils.config_loader import get_model, get_max_tokens

SYSTEM_PROMPT = """
You are the Operations assistant for a real estate SaaS startup.
Generate a concise daily CEO briefing using current system data.
Be terse. Be actionable. No filler.

Format exactly:
PENDING APPROVALS: <count> — <brief list of what they are>
TODAY: <calendar highlights or "No events loaded">
METRICS: <3 key numbers from the data>
TOP PRIORITY: <single most important thing CEO should do today>
"""


class OperationsAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="operations",
            system_prompt=SYSTEM_PROMPT,
            model=get_model("operations", fallback="claude-haiku-4-5-20251001"),
            max_tokens=get_max_tokens("operations", fallback=1024),
        )

    def _register_tools(self):
        self._tools = [
            Tool(
                name="get_system_stats",
                description="Get current BizOS stats: pending approvals, task counts, recent activity",
                input_schema={"type": "object", "properties": {}, "required": []},
                handler=self._collect_stats,
            ),
        ]

    def _collect_stats(self) -> dict:
        stats = get_stats()
        pending = get_pending_approvals()
        logs = get_agent_logs(limit=10)
        calendar = get_calendar_today()
        return {
            "stats": stats,
            "pending_approvals": [
                {"agent": p["agent"], "action": p["action_type"], "queued": p["created_at"][:16]}
                for p in pending
            ],
            "recent_activity": [
                {"agent": l["agent"], "action": l["action"], "time": l["timestamp"][:16]}
                for l in logs[:5]
            ],
            "calendar_today": calendar.get("events", []),
            "date": datetime.now().strftime("%A, %B %d %Y"),
        }

    def run(self, task_payload: dict) -> AgentResult:
        try:
            data = self._collect_stats()
            prompt = (
                f"Generate today's CEO briefing from this data:\n"
                f"{json.dumps(data, indent=2)}"
            )
            briefing = self._run_loop(prompt)

            send_slack_message(
                f"*BizOS Daily Briefing — {datetime.now().strftime('%b %d')}*\n\n{briefing}"
            )

            return AgentResult(
                agent="operations",
                action_type="daily_briefing",
                output={"briefing": briefing, "stats": data["stats"]},
                requires_approval=False,
                preview={"briefing": briefing},
            )
        except Exception as e:
            return AgentResult(
                agent="operations",
                action_type="daily_briefing",
                output={},
                requires_approval=False,
                error=str(e),
            )
