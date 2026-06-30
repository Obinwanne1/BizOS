"""
BizOS Background Scheduler
Runs agents on their cron schedules from config/agents.yaml.
Launch as a separate process alongside the Streamlit dashboard.
"""
import logging
import sys
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from orchestrator.router import dispatch
from orchestrator.state import init_db, get_db
from utils.config_loader import load_agents_config

import io
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [scheduler] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")),
        logging.FileHandler("data/scheduler.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

AGENT_PAYLOADS = {
    "lead_gen":   {"query": "Find 10 real estate professionals matching our ICP"},
    "content":    {"platform": "LinkedIn", "content_type": "Market Update"},
    "sales":      {},
    "marketing":  {"context": "Generate this week's marketing strategy for RE SaaS"},
    "product":    {},
    "operations": {},
}


def _run_agent(agent_name: str):
    logger.info("Scheduled run: %s", agent_name)
    payload = AGENT_PAYLOADS.get(agent_name, {})
    result = dispatch(agent_name, "scheduled", payload)
    status = result.get("status", "unknown")
    logger.info("Completed %s -> %s", agent_name, status)
    _update_schedule_log(agent_name)


def _update_schedule_log(agent_name: str):
    try:
        with get_db() as conn:
            conn.execute(
                """INSERT INTO agent_schedules (agent, last_run)
                   VALUES (?, datetime('now'))
                   ON CONFLICT(agent) DO UPDATE SET last_run=datetime('now')""",
                (agent_name,),
            )
    except Exception as e:
        logger.warning("Failed to update schedule log for %s: %s", agent_name, e)


def build_scheduler() -> BlockingScheduler:
    init_db()
    config = load_agents_config()
    agents_cfg = config.get("agents", {})

    scheduler = BlockingScheduler(timezone="America/New_York")

    for agent_name, cfg in agents_cfg.items():
        cron_expr = cfg.get("schedule")
        if not cron_expr:
            continue

        parts = cron_expr.strip().split()
        if len(parts) != 5:
            logger.warning("Invalid cron for %s: %r", agent_name, cron_expr)
            continue

        minute, hour, day, month, day_of_week = parts
        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            timezone="America/New_York",
        )
        scheduler.add_job(
            _run_agent,
            trigger=trigger,
            args=[agent_name],
            id=agent_name,
            name=f"BizOS:{agent_name}",
            misfire_grace_time=300,
            coalesce=True,
        )
        logger.info("Scheduled %s -> cron: %s", agent_name, cron_expr)

    return scheduler


if __name__ == "__main__":
    logger.info("BizOS Scheduler starting — %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    scheduler = build_scheduler()
    logger.info("Jobs registered: %d", len(scheduler.get_jobs()))
    for job in scheduler.get_jobs():
        logger.info("  %s -> next: %s", job.id, job.next_run_time)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
