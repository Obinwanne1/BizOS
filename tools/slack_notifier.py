import os
import requests
from dotenv import load_dotenv

load_dotenv()


def send_slack_message(text: str, blocks: list = None) -> dict:
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook:
        print(f"[Slack stub] {text}")
        return {"ok": True, "stub": True}

    payload = {"text": text}
    if blocks:
        payload["blocks"] = blocks

    try:
        resp = requests.post(webhook, json=payload, timeout=10)
        return {"ok": resp.status_code == 200, "status": resp.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def notify_approval_needed(agent: str, action: str, approval_id: str) -> dict:
    text = (
        f":bell: *Approval Needed*\n"
        f"Agent: `{agent}` | Action: `{action}`\n"
        f"Open BizOS dashboard to review → Approval ID: `{approval_id[:8]}...`"
    )
    return send_slack_message(text)
