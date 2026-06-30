import json
from agents.base import BaseAgent, AgentResult, Tool
from tools.airtable_crm import get_uncontacted_leads


SYSTEM_PROMPT = """
You are the Sales specialist for a real estate SaaS startup.
Write personalized, compelling outreach emails to real estate professionals.
Lead with THEIR pain point, not product features. Be specific and concise.
Always research the prospect before writing (use their title, company context).

Return JSON:
{
  "to": "email",
  "to_name": "name",
  "subject": "...",
  "body": "...",
  "tone": "professional|conversational|direct",
  "personalization_used": ["..."]
}
"""


class SalesAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="sales",
            system_prompt=SYSTEM_PROMPT,
            model="claude-sonnet-4-6",
            max_tokens=4096,
        )

    def _register_tools(self):
        self._tools = [
            Tool(
                name="get_uncontacted_leads",
                description="Get leads from CRM that have not been contacted yet",
                input_schema={
                    "type": "object",
                    "properties": {"limit": {"type": "integer", "default": 5}},
                    "required": [],
                },
                handler=self._get_leads,
            ),
        ]

    def _get_leads(self, limit: int = 5) -> dict:
        leads = get_uncontacted_leads(limit=limit)
        return {"leads": leads}

    def run(self, task_payload: dict) -> AgentResult:
        try:
            lead = task_payload.get("lead")
            if not lead:
                leads_data = self._get_leads(limit=1)
                leads = leads_data.get("leads", [])
                if not leads:
                    return AgentResult(
                        agent="sales",
                        action_type="send_outreach",
                        output={"message": "No uncontacted leads found"},
                        requires_approval=False,
                    )
                lead = leads[0]

            prompt = f"""
Write a personalized outreach email for this prospect:
Name: {lead.get('name', 'the prospect')}
Title: {lead.get('title', 'Real Estate Professional')}
Company: {lead.get('company', '')}
Email: {lead.get('email', '')}
Notes: {lead.get('notes', '')}

Our product: Real estate SaaS that helps RE professionals [automate workflows, win more deals, save time].
Return JSON only.
"""
            raw = self._run_loop(prompt)

            try:
                start = raw.find("{")
                end = raw.rfind("}") + 1
                email_obj = json.loads(raw[start:end]) if start >= 0 else {}
            except Exception:
                email_obj = {"body": raw, "to": lead.get("email", ""), "to_name": lead.get("name", "")}

            email_obj["lead_id"] = lead.get("id", "")

            return AgentResult(
                agent="sales",
                action_type="send_outreach",
                output={"email": email_obj, "lead": lead},
                requires_approval=True,
                preview={
                    "to": email_obj.get("to", ""),
                    "to_name": email_obj.get("to_name", ""),
                    "subject": email_obj.get("subject", ""),
                    "body": email_obj.get("body", ""),
                    "lead_id": lead.get("id", ""),
                    "action": "Send email via Gmail",
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
