"""Multi-agent workflow engine. Defines built-in workflows and runs them step by step."""
import re
import logging
from orchestrator.state import create_workflow_run, update_workflow_run

logger = logging.getLogger(__name__)

# Built-in workflow definitions
WORKFLOWS: dict[str, dict] = {
    "new_lead_pipeline": {
        "name": "New Lead Pipeline",
        "description": "Find leads → draft personalised sales outreach → generate follow-up content",
        "steps": [
            {
                "agent": "lead_gen",
                "task_type": "workflow",
                "payload": {"query": "Find 10 qualified real estate professionals matching our ICP"},
            },
            {
                "agent": "sales",
                "task_type": "workflow",
                "payload": {},
            },
            {
                "agent": "content",
                "task_type": "workflow",
                "payload": {"platform": "LinkedIn", "content_type": "Agent Tip"},
            },
        ],
    },
    "weekly_publish": {
        "name": "Weekly Content Publish",
        "description": "Generate 3 platform-specific posts → marketing strategy review",
        "steps": [
            {
                "agent": "content",
                "task_type": "workflow",
                "payload": {"platform": "LinkedIn", "content_type": "Market Update"},
            },
            {
                "agent": "content",
                "task_type": "workflow",
                "payload": {"platform": "Twitter", "content_type": "Agent Tip"},
            },
            {
                "agent": "content",
                "task_type": "workflow",
                "payload": {"platform": "Instagram", "content_type": "Industry News"},
            },
            {
                "agent": "marketing",
                "task_type": "workflow",
                "payload": {"context": "Review this week's content and plan next week's campaigns"},
            },
        ],
    },
    "friday_review": {
        "name": "Friday Review",
        "description": "Analyse user feedback → prioritise roadmap → generate CEO briefing",
        "steps": [
            {
                "agent": "product",
                "task_type": "workflow",
                "payload": {},
            },
            {
                "agent": "operations",
                "task_type": "workflow",
                "payload": {},
            },
        ],
    },
    "pipeline_and_marketing": {
        "name": "Pipeline + Marketing Sprint",
        "description": "Find leads + generate marketing strategy in parallel (sequential dispatch)",
        "steps": [
            {
                "agent": "lead_gen",
                "task_type": "workflow",
                "payload": {"query": "Find 10 real estate brokers and team leads in major US markets"},
            },
            {
                "agent": "marketing",
                "task_type": "workflow",
                "payload": {"context": "Plan campaigns to nurture the new leads added to CRM today"},
            },
        ],
    },
}


def _resolve_payload(template: dict, context: dict) -> dict:
    """Replace {step_N.key} references with values from prior step outputs."""
    resolved = {}
    for k, v in template.items():
        if isinstance(v, str) and "{" in v:
            def _sub(m):
                path = m.group(1).split(".")
                val = context
                for part in path:
                    if isinstance(val, dict):
                        val = val.get(part, "")
                    elif isinstance(val, list) and part.isdigit():
                        idx = int(part)
                        val = val[idx] if idx < len(val) else ""
                    else:
                        val = ""
                return str(val) if val != "" else ""
            resolved[k] = re.sub(r"\{([^}]+)\}", _sub, v)
        else:
            resolved[k] = v
    return resolved


def run_workflow(workflow_name: str, initial_payload: dict = None) -> dict:
    """Execute a named workflow sequentially. Returns a run summary."""
    from orchestrator.router import dispatch

    defn = WORKFLOWS.get(workflow_name)
    if not defn:
        return {"error": f"Unknown workflow: {workflow_name!r}", "available": list(WORKFLOWS)}

    run_id = create_workflow_run(workflow_name)
    steps = defn["steps"]
    step_results = []
    context = {"initial": initial_payload or {}}
    overall_status = "completed"

    logger.info("[workflow] starting %s (run %s, %d steps)", workflow_name, run_id[:8], len(steps))

    for i, step in enumerate(steps):
        agent = step["agent"]
        task_type = step["task_type"]
        payload = _resolve_payload(step.get("payload", {}), context)
        if initial_payload:
            payload = {**initial_payload, **payload}

        logger.info("[workflow] step %d/%d — %s", i + 1, len(steps), agent)
        result = dispatch(agent, task_type, payload)

        step_result = {
            "step": i + 1,
            "agent": agent,
            "status": result.get("status", "unknown"),
            "approval_id": result.get("approval_id"),
            "error": result.get("error"),
        }

        # Store output in context for downstream template resolution
        if result.get("status") == "completed" and result.get("output"):
            context[f"step_{i}"] = result["output"]
            step_result["output_keys"] = list(result["output"].keys())

        step_results.append(step_result)

        if result.get("status") == "failed":
            overall_status = "partial"
            logger.warning("[workflow] step %d failed: %s", i + 1, result.get("error"))

    update_workflow_run(run_id, overall_status, step_results)
    logger.info("[workflow] %s finished — status: %s", workflow_name, overall_status)

    pending = [s for s in step_results if s["status"] == "awaiting_approval"]
    completed = [s for s in step_results if s["status"] == "completed"]
    failed = [s for s in step_results if s["status"] == "failed"]

    return {
        "run_id": run_id,
        "workflow": workflow_name,
        "status": overall_status,
        "steps_total": len(steps),
        "steps_completed": len(completed),
        "steps_pending_approval": len(pending),
        "steps_failed": len(failed),
        "pending_approval_ids": [s["approval_id"] for s in pending if s.get("approval_id")],
        "step_results": step_results,
    }


def dispatch_intent(intent: str) -> dict:
    """Route a natural-language CEO intent to the right workflow or agent."""
    from agents.orchestrator import OrchestratorAgent
    agent = OrchestratorAgent()
    result = agent.run({"intent": intent})
    if result.error:
        return {"error": result.error}
    plan = result.output.get("plan", {})
    action = plan.get("action")

    if action == "run_workflow":
        wf = plan.get("workflow")
        if wf not in WORKFLOWS:
            return {"error": f"Orchestrator chose unknown workflow: {wf!r}", "plan": plan}
        wf_result = run_workflow(wf, plan.get("payload"))
        return {"action": action, "workflow": wf, "reasoning": plan.get("reasoning", ""), **wf_result}

    if action == "dispatch_agent":
        from orchestrator.router import dispatch
        ag = plan.get("agent")
        payload = plan.get("payload", {})
        dispatch_result = dispatch(ag, "orchestrated", payload)
        return {"action": action, "agent": ag, "reasoning": plan.get("reasoning", ""), **dispatch_result}

    return {"error": "Orchestrator returned unknown action", "plan": plan}
