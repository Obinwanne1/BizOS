import sqlite3
import json
import uuid
import logging
from pathlib import Path
from contextlib import contextmanager
from utils.validators import is_valid_uuid, validate_payload

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "bizos.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    agent TEXT NOT NULL,
    type TEXT NOT NULL,
    payload_json TEXT,
    status TEXT DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
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

CREATE TABLE IF NOT EXISTS workflow_runs (
    id TEXT PRIMARY KEY,
    workflow_name TEXT NOT NULL,
    status TEXT DEFAULT 'running',
    step_results_json TEXT DEFAULT '[]',
    started_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS agent_memory (
    id TEXT PRIMARY KEY,
    agent TEXT NOT NULL,
    memory_type TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    source TEXT DEFAULT 'system',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
"""


@contextmanager
def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
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
        # Migrate: add progress column to tasks if missing (SQLite has no IF NOT EXISTS for ALTER)
        try:
            conn.execute("ALTER TABLE tasks ADD COLUMN progress INTEGER DEFAULT 0")
        except Exception:
            pass  # column already exists


def create_task(agent: str, task_type: str, payload: dict) -> str:
    ok, err = validate_payload(payload)
    if not ok:
        raise ValueError(f"Invalid task payload: {err}")

    task_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO tasks (id, agent, type, payload_json) VALUES (?, ?, ?, ?)",
            (task_id, agent, task_type, json.dumps(payload)),
        )
    return task_id


def update_task_status(task_id: str, status: str):
    if not is_valid_uuid(task_id):
        raise ValueError(f"Invalid task_id: {task_id!r}")
    with get_db() as conn:
        conn.execute(
            "UPDATE tasks SET status=?, updated_at=datetime('now') WHERE id=?",
            (status, task_id),
        )


def update_task_progress(task_id: str, progress: int):
    if not is_valid_uuid(task_id):
        return
    progress = max(0, min(100, progress))
    with get_db() as conn:
        conn.execute(
            "UPDATE tasks SET progress=?, updated_at=datetime('now') WHERE id=?",
            (progress, task_id),
        )


def queue_approval(task_id: str, agent: str, action_type: str, preview: dict) -> str:
    ok, err = validate_payload(preview)
    if not ok:
        raise ValueError(f"Invalid approval preview: {err}")

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


def get_approval_by_id(approval_id: str) -> dict | None:
    if not is_valid_uuid(approval_id):
        return None
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM pending_approvals WHERE id=?", (approval_id,)
        ).fetchone()
    return dict(row) if row else None


def resolve_approval(approval_id: str, approved: bool, feedback: str = "") -> dict:
    if not is_valid_uuid(approval_id):
        raise ValueError(f"Invalid approval_id: {approval_id!r}")

    status = "approved" if approved else "rejected"

    with get_db() as conn:
        # Check it's still pending — prevents double-execution
        row = conn.execute(
            "SELECT status FROM pending_approvals WHERE id=?", (approval_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Approval {approval_id} not found")
        if row["status"] != "pending":
            raise ValueError(f"Approval {approval_id} already {row['status']}")

        conn.execute(
            "UPDATE pending_approvals SET status=?, ceo_feedback=?, reviewed_at=datetime('now') WHERE id=?",
            (status, feedback[:1000], approval_id),
        )
        updated = conn.execute(
            "SELECT * FROM pending_approvals WHERE id=?", (approval_id,)
        ).fetchone()
    return dict(updated)


def log_agent_action(agent: str, action: str, result: dict, approved_by: str = "system"):
    try:
        serialized = json.dumps(result)
    except (TypeError, ValueError):
        serialized = json.dumps({"error": "result not serializable"})

    with get_db() as conn:
        conn.execute(
            "INSERT INTO agent_logs (id, agent, action, result_json, approved_by) VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), agent, action, serialized, approved_by),
        )


def get_last_run_per_agent() -> dict[str, str]:
    """Return {agent_name: last_timestamp} in one query."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT agent, MAX(timestamp) as last_run FROM agent_logs GROUP BY agent"
        ).fetchall()
    return {r["agent"]: r["last_run"][:16] for r in rows}


def get_agent_logs(agent: str = None, limit: int = 50) -> list[dict]:
    limit = min(limit, 500)
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


def create_workflow_run(workflow_name: str) -> str:
    run_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO workflow_runs (id, workflow_name) VALUES (?, ?)",
            (run_id, workflow_name),
        )
    return run_id


def update_workflow_run(run_id: str, status: str, step_results: list):
    with get_db() as conn:
        completed_at = "datetime('now')" if status in ("completed", "failed", "partial") else "NULL"
        conn.execute(
            f"UPDATE workflow_runs SET status=?, step_results_json=?, completed_at=({'datetime(\"now\")' if status in ('completed','failed','partial') else 'NULL'}) WHERE id=?",
            (status, json.dumps(step_results), run_id),
        )


def get_workflow_runs(limit: int = 20) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM workflow_runs ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def save_memory(agent: str, memory_type: str, key: str, value: str,
                confidence: float = 1.0, source: str = "system") -> str:
    memory_id = str(uuid.uuid4())
    value_str = value if isinstance(value, str) else json.dumps(value)
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM agent_memory WHERE agent=? AND key=?", (agent, key)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE agent_memory SET value=?, confidence=?, source=?, updated_at=datetime('now') WHERE id=?",
                (value_str, confidence, source, existing["id"]),
            )
            return existing["id"]
        conn.execute(
            "INSERT INTO agent_memory (id, agent, memory_type, key, value, confidence, source) VALUES (?,?,?,?,?,?,?)",
            (memory_id, agent, memory_type, key, value_str, confidence, source),
        )
    return memory_id


def get_memories(agent: str, memory_type: str = None, limit: int = 20) -> list[dict]:
    limit = min(limit, 200)
    with get_db() as conn:
        if memory_type:
            rows = conn.execute(
                "SELECT * FROM agent_memory WHERE agent=? AND memory_type=? ORDER BY updated_at DESC LIMIT ?",
                (agent, memory_type, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM agent_memory WHERE agent=? ORDER BY updated_at DESC LIMIT ?",
                (agent, limit),
            ).fetchall()
    return [dict(r) for r in rows]


def get_all_memories(limit: int = 200) -> list[dict]:
    limit = min(limit, 500)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM agent_memory ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def delete_memory(memory_id: str) -> bool:
    if not is_valid_uuid(memory_id):
        return False
    with get_db() as conn:
        conn.execute("DELETE FROM agent_memory WHERE id=?", (memory_id,))
    return True


def get_stats() -> dict:
    with get_db() as conn:
        pending = conn.execute(
            "SELECT COUNT(*) as n FROM pending_approvals WHERE status='pending'"
        ).fetchone()["n"]
        total_tasks = conn.execute("SELECT COUNT(*) as n FROM tasks").fetchone()["n"]
        approved_today = conn.execute(
            "SELECT COUNT(*) as n FROM pending_approvals WHERE status='approved' AND date(reviewed_at)=date('now')"
        ).fetchone()["n"]
    return {
        "pending_approvals": pending,
        "total_tasks": total_tasks,
        "approved_today": approved_today,
    }
