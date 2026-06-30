from agents.base import BaseAgent, AgentResult, Tool
from tools.airtable_crm import get_uncontacted_leads
from utils.json_parser import extract_json
from utils.config_loader import get_model, get_max_tokens
from utils.validators import sanitize_email_body, sanitize_text

SYSTEM_PROMPT = """
You are the Sales specialist for a real estate SaaS startup.
Write personalized, compelling outreach emails to real estate professionals.
Lead with THEIR pain point — never open with product features.
Be specific: reference their title, company, and typical workflow challenges.

Return raw JSON only (no markdown fences):
{
  "to": "email address",
  "to_name": "full name",
  "subject": "subject line under 60 chars",
  "body": "plain text email body, 3-4 short paragraphs",
  "tone": "professional|conversational|direct",
  "personalization_used": ["what you referenced about the prospect"]
}
"""


class SalesAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="sales",
            system_prompt=SYSTEM_PROMPT,
            model=get_model("sales"),
            max_tokens=get_max_tokens("sales"),
        )

    def _register_tools(self):
        self._tools = [
            Tool(
                name="get_uncontacted_leads",
                description="Get leads from CRM that have not been contacted yet",
                input_schema={
                    "type": "object",
                    "properties": {"limit": {"type": "integer"}},
                    "required": [],
                },
                handler=lambda limit=5: {"leads": get_uncontacted_leads(limit=limit)},
            ),
        ]

    def run(self, task_payload: dict) -> AgentResult:
        try:
            lead = task_payload.get("lead")
            if not lead:
                leads = get_uncontacted_leads(limit=1)
                if not leads:
                    return AgentResult(
                        agent="sales",
                        action_type="send_outreach",
                        output={"message": "No uncontacted leads in CRM"},
                        requires_approval=False,
                    )
                lead = leads[0]

            prompt = (
                f"Write a personalized outreach email for this real estate professional:\n"
                f"Name: {sanitize_text(lead.get('name', ''))}\n"
                f"Title: {sanitize_text(lead.get('title', 'Real Estate Professional'))}\n"
                f"Company: {sanitize_text(lead.get('company', ''))}\n"
                f"Email: {sanitize_text(lead.get('email', ''))}\n"
                f"Notes: {sanitize_text(lead.get('notes', ''))}\n\n"
                "Our product: Real estate SaaS that automates lead follow-up, listing management, "
                "and client communication for RE professionals — saves 8+ hrs/week.\n"
                "Return raw JSON only."
            )
            raw = self._run_loop(prompt)
            email_obj = extract_json(raw, expect="object")

            if not email_obj.get("body"):
                email_obj = {
                    "body": raw,
                    "to": lead.get("email", ""),
                    "to_name": lead.get("name", ""),
                    "subject": f"Quick question for {lead.get('name', 'you')}",
                }

            # Sanitize body — strip any HTML before storing/sending
            email_obj["body"] = sanitize_email_body(email_obj.get("body", ""))
            email_obj["lead_id"] = lead.get("id", "")

            return AgentResult(
                agent="sales",
                action_type="send_outreach",
                output={"email": email_obj, "lead": lead},
                requires_approval=True,
                preview={
                    "to": sanitize_text(email_obj.get("to", "")),
                    "to_name": sanitize_text(email_obj.get("to_name", "")),
                    "subject": sanitize_text(email_obj.get("subject", ""), max_length=200),
                    "body": email_obj.get("body", ""),
                    "tone": email_obj.get("tone", ""),
                    "personalization_used": email_obj.get("personalization_used", []),
                    "lead_id": lead.get("id", ""),
                    "action": "Create Gmail draft",
                },
            )
        except Exception as e:
            return AgentResult(
                agent="sales",
                action_type="send_outreach",
                output={},
                requires_approval=False,
                error=str(e),
            )

    def execute_approved(self, action_type: str, preview: dict) -> dict:
        from tools.google_workspace import create_gmail_draft
        from tools.airtable_crm import mark_lead_contacted

        result = create_gmail_draft(
            to=preview.get("to", ""),
            subject=preview.get("subject", ""),
            body=preview.get("body", ""),
        )
        if preview.get("lead_id"):
            mark_lead_contacted(preview["lead_id"])
        return {"draft_created": True, "gmail_result": result}
