"""Orchestrator meta-agent. Routes CEO intent to the right workflow or agent."""
from agents.base import BaseAgent, AgentResult, Tool
from utils.json_parser import extract_json
from utils.config_loader import get_orchestrator_model

SYSTEM_PROMPT = """
You are the BizOS Orchestrator — the meta-agent for a real estate SaaS AI operating system.
Your job: analyse the CEO's intent and decide which workflow or single agent to trigger.

Available workflows:
- new_lead_pipeline: Find leads → sales outreach → follow-up content
- weekly_publish: Generate 3 platform posts → marketing review
- friday_review: Product feedback analysis → roadmap update → CEO briefing
- pipeline_and_marketing: Lead gen + marketing strategy sprint

Available agents (for single-agent dispatch):
- lead_gen: Find and qualify new real estate leads
- content: Write social media content (LinkedIn/Twitter/Instagram)
- sales: Draft personalized outreach emails
- marketing: Generate weekly campaign strategy
- product: Analyse feedback and prioritize roadmap
- operations: Generate daily CEO briefing → Slack

Decision rules:
- Multi-step goal → run_workflow
- Single focused task → dispatch_agent
- Ambiguous → pick the closest match, explain why

Return raw JSON only:
{
  "action": "run_workflow" | "dispatch_agent",
  "workflow": "workflow_name_if_applicable",
  "agent": "agent_name_if_applicable",
  "payload": {},
  "reasoning": "one sentence explaining the decision"
}
"""


class OrchestratorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="orchestrator",
            system_prompt=SYSTEM_PROMPT,
            model=get_orchestrator_model(),
            max_tokens=1024,
        )

    def _register_tools(self):
        self._tools = [
            Tool(
                name="list_workflows",
                description="List available workflows with descriptions to inform routing decision",
                input_schema={"type": "object", "properties": {}, "required": []},
                handler=self._list_workflows,
            ),
        ]

    def _list_workflows(self) -> dict:
        from orchestrator.workflow import WORKFLOWS
        return {
            name: {"description": defn["description"], "steps": len(defn["steps"])}
            for name, defn in WORKFLOWS.items()
        }

    def run(self, task_payload: dict) -> AgentResult:
        try:
            intent = task_payload.get("intent", "").strip()
            if not intent:
                return AgentResult(
                    agent="orchestrator",
                    action_type="route_intent",
                    output={},
                    requires_approval=False,
                    error="No intent provided",
                )
            raw = self._run_loop(intent)
            plan = extract_json(raw, expect="object")
            if not plan.get("action"):
                plan = {"action": "dispatch_agent", "agent": "operations", "payload": {},
                        "reasoning": "Fallback: could not parse intent"}
            return AgentResult(
                agent="orchestrator",
                action_type="route_intent",
                output={"plan": plan},
                requires_approval=False,
                preview=plan,
            )
        except Exception as e:
            return AgentResult(
                agent="orchestrator",
                action_type="route_intent",
                output={},
                requires_approval=False,
                error=str(e),
            )
