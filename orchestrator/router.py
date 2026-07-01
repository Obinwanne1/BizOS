import json
import logging
from pathlib import Path
from orchestrator.state import (
    create_task, update_task_status, queue_approval,
    log_agent_action, get_approval_by_id,
)
from agents.base import AgentResult
from utils.validators import is_valid_agent, validate_approval_id

logger = logging.getLogger(__name__)


def get_agent(agent_name: str):
    if not is_valid_agent(agent_name):
        raise ValueError(f"Unknown agent: {agent_name!r}")

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
    return registry[agent_name]()


def dispatch(agent_name: str, task_type: str, payload: dict) -> dict:
    if not is_valid_agent(agent_name):
        return {"status": "failed", "error": f"Unknown agent: {agent_name!r}"}

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
            log_agent_action(agent_name, task_type, {"approval_id": approval_id})
            return {
                "status": "awaiting_approval",
                "approval_id": approval_id,
                "preview": result.preview,
            }

        update_task_status(task_id, "completed")
        log_agent_action(agent_name, task_type, result.output)
        return {"status": "completed", "output": result.output}

    except EnvironmentError as e:
        # Missing API key — surface clearly
        update_task_status(task_id, "failed")
        log_agent_action(agent_name, task_type, {"error": str(e)})
        return {"status": "failed", "error": str(e)}
    except Exception as e:
        logger.exception("[router] dispatch failed for %s", agent_name)
        update_task_status(task_id, "failed")
        log_agent_action(agent_name, task_type, {"error": str(e)})
        return {"status": "failed", "error": str(e)}


def dispatch_with_agent(agent, agent_name: str, task_type: str, payload: dict) -> dict:
    """Same as dispatch() but uses a pre-configured agent instance (e.g. with _on_chunk set)."""
    task_id = create_task(agent_name, task_type, payload)
    update_task_status(task_id, "running")
    try:
        result: AgentResult = agent.run(payload)
        if result.error:
            update_task_status(task_id, "failed")
            log_agent_action(agent_name, task_type, {"error": result.error})
            return {"status": "failed", "error": result.error}
        if result.requires_approval:
            approval_id = queue_approval(task_id, agent_name, result.action_type, result.preview)
            update_task_status(task_id, "awaiting_approval")
            log_agent_action(agent_name, task_type, {"approval_id": approval_id})
            return {"status": "awaiting_approval", "approval_id": approval_id, "preview": result.preview}
        update_task_status(task_id, "completed")
        log_agent_action(agent_name, task_type, result.output)
        return {"status": "completed", "output": result.output}
    except EnvironmentError as e:
        update_task_status(task_id, "failed")
        log_agent_action(agent_name, task_type, {"error": str(e)})
        return {"status": "failed", "error": str(e)}
    except Exception as e:
        logger.exception("[router] dispatch_with_agent failed for %s", agent_name)
        update_task_status(task_id, "failed")
        log_agent_action(agent_name, task_type, {"error": str(e)})
        return {"status": "failed", "error": str(e)}


def execute_approved(approval_id: str) -> dict:
    ok, err = validate_approval_id(approval_id)
    if not ok:
        return {"error": err}

    approval = get_approval_by_id(approval_id)
    if not approval:
        return {"error": "Approval not found"}

    # Guard: only execute if still pending (resolve_approval enforces this too, but belt-and-suspenders)
    if approval["status"] != "pending":
        return {"error": f"Approval already {approval['status']} — cannot re-execute"}

    preview = json.loads(approval["preview_json"])

    try:
        agent = get_agent(approval["agent"])
        result = agent.execute_approved(approval["action_type"], preview)
        log_agent_action(approval["agent"], f"execute:{approval['action_type']}", result, "ceo")
        _trigger_handoffs(approval["agent"], approval["action_type"], preview, result)
        return result
    except Exception as e:
        logger.exception("[router] execute_approved failed for approval %s", approval_id)
        return {"error": str(e)}


def _trigger_handoffs(agent: str, action_type: str, preview: dict, result: dict):
    """Fire downstream agents after certain approvals execute."""
    try:
        if agent == "lead_gen" and action_type == "add_leads_to_crm":
            leads = preview.get("leads", [])
            if not leads:
                return
            lead = leads[0]
            # Only hand off if lead has a real Airtable record ID (not a mock ID)
            lead_id = lead.get("id", "")
            if not lead_id or lead_id.startswith("mock") or not lead_id.startswith("rec"):
                logger.info("[handoff] skipped — lead has no real Airtable ID (mock data)")
                return
            logger.info("[handoff] lead_gen → sales: %d new lead(s) in CRM", len(leads))
            dispatch("sales", "handoff_from_lead_gen", {"lead": lead})

    except Exception as e:
        logger.warning("[handoff] failed: %s", e)
