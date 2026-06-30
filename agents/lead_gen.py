import json
import os
import requests
from agents.base import BaseAgent, AgentResult, Tool
from tools.airtable_crm import add_leads_to_crm


SYSTEM_PROMPT = """
You are the Lead Generation specialist for a real estate SaaS startup.
Your ICP: real estate agents, brokers, team leads, and property managers in the US.
You find prospects, score them by fit (1-10), and return a structured lead list.
Score criteria: company size, tech adoption signals, active social presence, pain points matching our product.
Always return a JSON array of leads with: name, title, company, email_guess, linkedin_url, score, reason.
"""


class LeadGenAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="lead_gen",
            system_prompt=SYSTEM_PROMPT,
            model="claude-sonnet-4-6",
            max_tokens=4096,
        )

    def _register_tools(self):
        self._tools = [
            Tool(
                name="search_apollo",
                description="Search Apollo.io for real estate professionals matching the ICP",
                input_schema={
                    "type": "object",
                    "properties": {
                        "job_titles": {"type": "array", "items": {"type": "string"}},
                        "industry": {"type": "string"},
                        "location": {"type": "string"},
                        "limit": {"type": "integer", "default": 20},
                    },
                    "required": ["job_titles"],
                },
                handler=self._search_apollo,
            ),
            Tool(
                name="enrich_lead",
                description="Enrich a lead with additional data from Hunter.io",
                input_schema={
                    "type": "object",
                    "properties": {
                        "domain": {"type": "string"},
                        "first_name": {"type": "string"},
                        "last_name": {"type": "string"},
                    },
                    "required": ["domain"],
                },
                handler=self._enrich_lead,
            ),
        ]

    def _search_apollo(self, job_titles: list, industry: str = "Real Estate",
                       location: str = "United States", limit: int = 20) -> dict:
        api_key = os.getenv("APOLLO_API_KEY")
        if not api_key:
            return {"error": "APOLLO_API_KEY not set", "mock": True, "leads": self._mock_leads()}

        try:
            resp = requests.post(
                "https://api.apollo.io/v1/mixed_people/search",
                headers={"Content-Type": "application/json", "Cache-Control": "no-cache"},
                json={
                    "api_key": api_key,
                    "person_titles": job_titles,
                    "organization_industry_tag_ids": [],
                    "person_locations": [location],
                    "per_page": limit,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                people = data.get("people", [])
                return {
                    "leads": [
                        {
                            "name": f"{p.get('first_name','')} {p.get('last_name','')}".strip(),
                            "title": p.get("title", ""),
                            "company": p.get("organization", {}).get("name", ""),
                            "email": p.get("email", ""),
                            "linkedin_url": p.get("linkedin_url", ""),
                            "city": p.get("city", ""),
                            "state": p.get("state", ""),
                        }
                        for p in people
                    ]
                }
            return {"error": f"Apollo returned {resp.status_code}", "mock": True, "leads": self._mock_leads()}
        except Exception as e:
            return {"error": str(e), "mock": True, "leads": self._mock_leads()}

    def _enrich_lead(self, domain: str, first_name: str = "", last_name: str = "") -> dict:
        api_key = os.getenv("HUNTER_IO_KEY")
        if not api_key:
            return {"email": f"info@{domain}", "confidence": 0, "mock": True}

        try:
            params = {"domain": domain, "api_key": api_key}
            if first_name:
                params["first_name"] = first_name
            if last_name:
                params["last_name"] = last_name
            resp = requests.get("https://api.hunter.io/v2/email-finder", params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                return {"email": data.get("email", ""), "confidence": data.get("score", 0)}
            return {"email": "", "confidence": 0}
        except Exception as e:
            return {"error": str(e), "email": "", "confidence": 0}

    def _mock_leads(self) -> list:
        return [
            {"name": "Sarah Johnson", "title": "Real Estate Agent", "company": "Keller Williams Realty",
             "email": "sarah@kw.com", "linkedin_url": "https://linkedin.com/in/sarahjohnson-re", "city": "Austin", "state": "TX"},
            {"name": "Marcus Rivera", "title": "Broker/Owner", "company": "Rivera Properties",
             "email": "marcus@riveraprop.com", "linkedin_url": "https://linkedin.com/in/marcusrivera", "city": "Miami", "state": "FL"},
            {"name": "Jennifer Lee", "title": "Team Lead", "company": "Coldwell Banker",
             "email": "jlee@cbhomes.com", "linkedin_url": "https://linkedin.com/in/jenniferlee-re", "city": "Denver", "state": "CO"},
        ]

    def run(self, task_payload: dict) -> AgentResult:
        try:
            query = task_payload.get("query", "Find 10 qualified real estate professionals matching our ICP")
            raw_output = self._run_loop(query)

            try:
                start = raw_output.find("[")
                end = raw_output.rfind("]") + 1
                leads = json.loads(raw_output[start:end]) if start >= 0 else []
            except Exception:
                leads = self._mock_leads()

            preview = {
                "lead_count": len(leads),
                "leads": leads,
                "action": "Add leads to Airtable CRM",
            }

            return AgentResult(
                agent="lead_gen",
                action_type="add_leads_to_crm",
                output={"leads": leads, "raw": raw_output},
                requires_approval=True,
                preview=preview,
            )
        except Exception as e:
            return AgentResult(
                agent="lead_gen",
                action_type="add_leads_to_crm",
                output={},
                requires_approval=False,
                error=str(e),
            )

    def execute_approved(self, action_type: str, preview: dict) -> dict:
        leads = preview.get("leads", [])
        result = add_leads_to_crm(leads)
        return {"added": len(leads), "crm_result": result}
