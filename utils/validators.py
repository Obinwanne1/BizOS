"""Input validation and security checks."""
import re
import html
from typing import Any

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
VALID_AGENTS = {"lead_gen", "content", "sales", "marketing", "product", "operations"}
VALID_STATUSES = {"pending", "running", "completed", "failed", "awaiting_approval"}
MAX_PAYLOAD_BYTES = 64 * 1024  # 64 KB

import json


def is_valid_uuid(value: str) -> bool:
    return bool(UUID_RE.match(value)) if isinstance(value, str) else False


def is_valid_agent(name: str) -> bool:
    return name in VALID_AGENTS


def validate_payload(payload: dict) -> tuple[bool, str]:
    """Returns (ok, error_message)."""
    if not isinstance(payload, dict):
        return False, "Payload must be a dict"
    try:
        size = len(json.dumps(payload).encode("utf-8"))
    except Exception:
        return False, "Payload not JSON-serializable"
    if size > MAX_PAYLOAD_BYTES:
        return False, f"Payload too large ({size} bytes, max {MAX_PAYLOAD_BYTES})"
    return True, ""


def sanitize_email_body(body: str) -> str:
    """Strip HTML tags from email body to prevent injection via email clients."""
    if not isinstance(body, str):
        return ""
    # Remove script tags and content
    body = re.sub(r"<script[\s\S]*?</script>", "", body, flags=re.I)
    # Remove all other HTML tags
    body = re.sub(r"<[^>]+>", "", body)
    # Decode any HTML entities left
    return html.unescape(body).strip()


def sanitize_text(value: str, max_length: int = 2000) -> str:
    if not isinstance(value, str):
        return ""
    return value[:max_length].strip()


def validate_approval_id(approval_id: str) -> tuple[bool, str]:
    if not isinstance(approval_id, str) or not approval_id:
        return False, "approval_id must be a non-empty string"
    if not is_valid_uuid(approval_id):
        return False, "approval_id must be a valid UUID"
    return True, ""
