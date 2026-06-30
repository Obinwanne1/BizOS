from orchestrator.state import resolve_approval, log_agent_action
from orchestrator.router import execute_approved


def approve(approval_id: str, feedback: str = "") -> dict:
    record = resolve_approval(approval_id, approved=True, feedback=feedback)
    result = execute_approved(approval_id)
    return {"approval": record, "execution": result}


def reject(approval_id: str, feedback: str) -> dict:
    record = resolve_approval(approval_id, approved=False, feedback=feedback)
    log_agent_action(record["agent"], f"rejected:{record['action_type']}", {"feedback": feedback}, "ceo")
    return {"approval": record, "status": "rejected"}
