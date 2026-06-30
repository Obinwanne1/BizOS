import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import json
from orchestrator.state import (
    init_db, create_task, update_task_status,
    queue_approval, get_pending_approvals,
    resolve_approval, log_agent_action, get_stats
)

# Use temp DB for tests
import orchestrator.state as state_module
state_module.DB_PATH = state_module.Path(__file__).parent.parent / "data" / "test_bizos.db"


@pytest.fixture(autouse=True)
def fresh_db():
    db = state_module.DB_PATH
    if db.exists():
        db.unlink()
    init_db()
    yield
    if db.exists():
        db.unlink()


def test_create_task():
    task_id = create_task("lead_gen", "find_leads", {"query": "test"})
    assert task_id
    assert len(task_id) == 36


def test_task_status_update():
    task_id = create_task("content", "generate", {})
    update_task_status(task_id, "completed")
    with state_module.get_db() as conn:
        row = conn.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
    assert row["status"] == "completed"


def test_approval_queue_and_resolve():
    task_id = create_task("sales", "send_email", {})
    preview = {"to": "test@test.com", "subject": "Hello", "body": "Test email"}
    approval_id = queue_approval(task_id, "sales", "send_outreach", preview)
    assert approval_id

    pending = get_pending_approvals()
    assert any(p["id"] == approval_id for p in pending)

    resolved = resolve_approval(approval_id, approved=True)
    assert resolved["status"] == "approved"

    pending_after = get_pending_approvals()
    assert not any(p["id"] == approval_id for p in pending_after)


def test_reject_approval():
    task_id = create_task("sales", "send_email", {})
    approval_id = queue_approval(task_id, "sales", "send_outreach", {"subject": "test"})
    resolved = resolve_approval(approval_id, approved=False, feedback="Too aggressive tone")
    assert resolved["status"] == "rejected"
    assert resolved["ceo_feedback"] == "Too aggressive tone"


def test_agent_log():
    log_agent_action("operations", "daily_briefing", {"briefing": "test"})
    from orchestrator.state import get_agent_logs
    logs = get_agent_logs("operations")
    assert len(logs) >= 1
    assert logs[0]["action"] == "daily_briefing"


def test_get_stats():
    init_db()
    stats = get_stats()
    assert "pending_approvals" in stats
    assert "total_tasks" in stats
