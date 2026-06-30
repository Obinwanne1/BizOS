import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).parent.parent / "data" / "bizos.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    agent TEXT NOT NULL,
    type TEXT NOT NULL,
    payload_json TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pending_approvals (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    agent TEXT NOT NULL,
    action_type TEXT NOT NULL,
    preview_json TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    ceo_feedback TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    reviewed_at TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS agent_logs (
    id TEXT PRIMARY KEY,
    agent TEXT NOT NULL,
    action TEXT NOT NULL,
    result_json TEXT,
    approved_by TEXT,
    timestamp TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_schedules (
    agent TEXT PRIMARY KEY,
    cron_expr TEXT,
    last_run TEXT,
    next_run TEXT,
    enabled INTEGER DEFAULT 1
);
"""


@contextmanager
def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript(SCHEMA)


def create_task(agent: str, task_type: str, payload: dict) -> str:
    task_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO tasks (id, agent, type, payload_json) VALUES (?, ?, ?, ?)",
            (task_id, agent, task_type, json.dumps(payload)),
        )
    return task_id


def update_task_status(task_id: str, status: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE tasks SET status=?, updated_at=datetime('now') WHERE id=?",
            (status, task_id),
        )


def queue_approval(task_id: str, agent: str, action_type: str, preview: dict) -> str:
    approval_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO pending_approvals (id, task_id, agent, action_type, preview_json) VALUES (?,?,?,?,?)",
            (approval_id, task_id, agent, action_type, json.dumps(preview)),
        )
    return approval_id


def get_pending_approvals() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM pending_approvals WHERE status='pending' ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def resolve_approval(approval_id: str, approved: bool, feedback: str = "") -> dict:
    status = "approved" if approved else "rejected"
    with get_db() as conn:
        conn.execute(
            "UPDATE pending_approvals SET status=?, ceo_feedback=?, reviewed_at=datetime('now') WHERE id=?",
            (status, feedback, approval_id),
        )
        row = conn.execute(
            "SELECT * FROM pending_approvals WHERE id=?", (approval_id,)
        ).fetchone()
    return dict(row)


def log_agent_action(agent: str, action: str, result: dict, approved_by: str = "system"):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO agent_logs (id, agent, action, result_json, approved_by) VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), agent, action, json.dumps(result), approved_by),
        )


def get_agent_logs(agent: str = None, limit: int = 50) -> list[dict]:
    with get_db() as conn:
        if agent:
            rows = conn.execute(
                "SELECT * FROM agent_logs WHERE agent=? ORDER BY timestamp DESC LIMIT ?",
                (agent, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM agent_logs ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    with get_db() as conn:
        pending = conn.execute(
            "SELECT COUNT(*) as n FROM pending_approvals WHERE status='pending'"
        ).fetchone()["n"]
        total_tasks = conn.execute("SELECT COUNT(*) as n FROM tasks").fetchone()["n"]
        approved_today = conn.execute(
            "SELECT COUNT(*) as n FROM pending_approvals WHERE status='approved' AND date(reviewed_at)=date('now')"
        ).fetchone()["n"]
    return {"pending_approvals": pending, "total_tasks": total_tasks, "approved_today": approved_today}
