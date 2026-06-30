import os
from dotenv import load_dotenv

load_dotenv()

try:
    from pyairtable import Api
    AIRTABLE_AVAILABLE = True
except ImportError:
    AIRTABLE_AVAILABLE = False


def _get_table(table_name: str):
    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    if not api_key or not base_id or not AIRTABLE_AVAILABLE:
        return None
    api = Api(api_key)
    return api.table(base_id, table_name)


def add_leads_to_crm(leads: list) -> dict:
    table = _get_table("Leads")
    if not table:
        print(f"[Airtable stub] Would add {len(leads)} leads to CRM")
        return {"added": len(leads), "stub": True}

    added = 0
    errors = []
    for lead in leads:
        try:
            table.create({
                "Name": lead.get("name", ""),
                "Title": lead.get("title", ""),
                "Company": lead.get("company", ""),
                "Email": lead.get("email", ""),
                "LinkedIn": lead.get("linkedin_url", ""),
                "Source": "Lead Gen Agent",
                "Stage": "New",
                "Score": lead.get("score", 5),
                "Notes": lead.get("reason", ""),
            })
            added += 1
        except Exception as e:
            errors.append(str(e))

    return {"added": added, "errors": errors}


def get_uncontacted_leads(limit: int = 5) -> list:
    table = _get_table("Leads")
    if not table:
        return [
            {"id": "mock-1", "name": "Sarah Johnson", "title": "Real Estate Agent",
             "company": "Keller Williams", "email": "sarah@kw.com", "notes": "Active on LinkedIn"},
            {"id": "mock-2", "name": "Marcus Rivera", "title": "Broker/Owner",
             "company": "Rivera Properties", "email": "marcus@riveraprop.com", "notes": ""},
        ][:limit]

    try:
        records = table.all(formula="{Stage}='New'", max_records=limit)
        return [
            {
                "id": r["id"],
                "name": r["fields"].get("Name", ""),
                "title": r["fields"].get("Title", ""),
                "company": r["fields"].get("Company", ""),
                "email": r["fields"].get("Email", ""),
                "notes": r["fields"].get("Notes", ""),
            }
            for r in records
        ]
    except Exception as e:
        return []


def mark_lead_contacted(lead_id: str) -> dict:
    table = _get_table("Leads")
    if not table:
        print(f"[Airtable stub] Marking lead {lead_id} as Contacted")
        return {"updated": True, "stub": True}

    try:
        table.update(lead_id, {"Stage": "Contacted"})
        return {"updated": True}
    except Exception as e:
        return {"updated": False, "error": str(e)}


def get_crm_stats() -> dict:
    table = _get_table("Leads")
    if not table:
        return {"total": 12, "new": 4, "contacted": 5, "demo": 2, "won": 1, "stub": True}

    try:
        all_records = table.all()
        stages = {}
        for r in all_records:
            stage = r["fields"].get("Stage", "Unknown")
            stages[stage] = stages.get(stage, 0) + 1
        return {"total": len(all_records), "by_stage": stages}
    except Exception as e:
        return {"error": str(e)}
