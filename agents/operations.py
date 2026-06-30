import json
from datetime import datetime
from agents.base import BaseAgent, AgentResult, Tool
from orchestrator.state import get_pending_approvals, get_agent_logs, get_stats
from tools.slack_notifier import send_slack_message


SYSTEM_PROMPT = """
You are the Operations assistant for a real estate SaaS startup.
Generate a concise daily CEO briefing. Be terse. Be actionable.
Format:
- PENDING APPROVALS: count + what they are
- TODAY: key calendar/priority items
- METRICS: top 3 KPIs
- TOP PRIORITY: one thing CEO should focus on today
"""


class OperationsAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="operations",
            system_prompt=SYSTEM_PROMPT,
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
        )

    def _register_tools(self):
        self._tools = [
            Tool(
                name="get_system_stats",
                description="Get current BizOS system stats: pending approvals, tasks, recent logs",
                input_schema={"type": "object", "properties": {}, "required": []},
                handler=self._get_stats,
            ),
        ]

    def _get_stats(self) -> dict:
        stats = get_stats()
        pending = get_pending_approvals()
        logs = get_agent_logs(limit=10)
        return {
            "stats": stats,
            "pending_approvals": [
                {"agent": p["agent"], "action": p["action_type"], "created": p["created_at"]}
                for p in pending
            ],
            "recent_activity": [
                {"agent": l["agent"], "action": l["action"], "time": l["timestamp"]}
                for l in logs[:5]
            ],
        }

    def run(self, task_payload: dict) -> AgentResult:
        try:
            stats = self._get_stats()
            briefing_prompt = f"""
Generate today's CEO briefing. Current data:
{json.dumps(stats, indent=2)}

Date: {datetime.now().strftime('%A, %B %d %Y')}
"""
            briefing = self._run_loop(briefing_prompt)

            send_slack_message(f"*BizOS Daily Briefing — {datetime.now().strftime('%b %d')}*\n\n{briefing}")

            return AgentResult(
                agent="operations",
                action_type="daily_briefing",
                output={"briefing": briefing, "stats": stats},
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
