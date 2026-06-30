import yaml
from pathlib import Path
from orchestrator.state import (
    create_task, update_task_status, queue_approval,
    log_agent_action, get_pending_approvals
)
from agents.base import AgentResult

CONFIG_PATH = Path(__file__).parent.parent / "config" / "agents.yaml"


def load_agent_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_agent(agent_name: str):
    from agents.lead_gen import LeadGenAgent
    from agents.content import ContentAgent
    from agents.sales import SalesAgent
    from agents.marketing import MarketingAgent
    from agents.product import ProductAgent
    from agents.operations import OperationsAgent

    registry = {
        "lead_gen": LeadGenAgent,
        "content": ContentAgent,
        "sales": SalesAgent,
        "marketing": MarketingAgent,
        "product": ProductAgent,
        "operations": OperationsAgent,
    }
    cls = registry.get(agent_name)
    if not cls:
        raise ValueError(f"Unknown agent: {agent_name}")
    return cls()


def dispatch(agent_name: str, task_type: str, payload: dict) -> dict:
    task_id = create_task(agent_name, task_type, payload)
    update_task_status(task_id, "running")

    try:
        agent = get_agent(agent_name)
        result: AgentResult = agent.run(payload)

        if result.error:
            update_task_status(task_id, "failed")
            log_agent_action(agent_name, task_type, {"error": result.error})
            return {"status": "failed", "error": result.error}

        if result.requires_approval:
            approval_id = queue_approval(task_id, agent_name, result.action_type, result.preview)
            update_task_status(task_id, "awaiting_approval")
            log_agent_action(agent_name, task_type, {"approval_id": approval_id, "output": result.output})
            return {"status": "awaiting_approval", "approval_id": approval_id, "preview": result.preview}

        update_task_status(task_id, "completed")
        log_agent_action(agent_name, task_type, result.output)
        return {"status": "completed", "output": result.output}

    except Exception as e:
        update_task_status(task_id, "failed")
        log_agent_action(agent_name, task_type, {"error": str(e)})
        return {"status": "failed", "error": str(e)}


def execute_approved(approval_id: str) -> dict:
    from orchestrator.state import get_db
    import json

    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM pending_approvals WHERE id=?", (approval_id,)
        ).fetchone()

    if not row:
        return {"error": "Approval not found"}

    approval = dict(row)
    output = json.loads(approval["preview_json"])

    agent = get_agent(approval["agent"])
    if hasattr(agent, "execute_approved"):
        result = agent.execute_approved(approval["action_type"], output)
        log_agent_action(approval["agent"], f"execute:{approval['action_type']}", result, "ceo")
        return result

    return {"status": "executed", "note": "Agent has no execute_approved — action was approval-only"}
