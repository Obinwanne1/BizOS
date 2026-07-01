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
        return {"total": 12, "new": 4, "contacted": 5, "demo": 2, "won": 1, "stub": True,
                "by_stage": {"New": 4, "Contacted": 3, "Replied": 2, "Demo Scheduled": 2, "Won": 1}}

    try:
        all_records = table.all()
        stages = {}
        for r in all_records:
            stage = r["fields"].get("Stage", "Unknown")
            stages[stage] = stages.get(stage, 0) + 1
        return {"total": len(all_records), "by_stage": stages}
    except Exception as e:
        return {"error": str(e)}


_STUB_LEADS_BY_STAGE = {
    "New": [
        {"name": "Sarah Chen", "title": "Broker", "company": "Chen Realty", "email": "s.chen@chenrealty.com", "score": 82},
        {"name": "Marcus Webb", "title": "Team Lead", "company": "Webb Group", "email": "m.webb@webb.com", "score": 75},
        {"name": "Diana Torres", "title": "Agent", "company": "Torres RE", "email": "d.torres@tresalty.com", "score": 68},
        {"name": "Kevin Park", "title": "Broker-Owner", "company": "Park Properties", "email": "k.park@parkprop.com", "score": 91},
    ],
    "Contacted": [
        {"name": "Lisa Monroe", "title": "Managing Broker", "company": "Monroe & Co", "email": "l.monroe@monroe.com", "score": 88},
        {"name": "James Okafor", "title": "Realtor", "company": "Okafor Group", "email": "j.okafor@okafor.com", "score": 72},
        {"name": "Priya Nair", "title": "Broker", "company": "Nair Homes", "email": "p.nair@nairhomes.com", "score": 79},
    ],
    "Replied": [
        {"name": "Tom Bradley", "title": "VP Sales", "company": "Bradley RE", "email": "t.bradley@bre.com", "score": 85},
        {"name": "Angela Reyes", "title": "Broker", "company": "Reyes Realty", "email": "a.reyes@reyesrealty.com", "score": 77},
    ],
    "Demo Scheduled": [
        {"name": "David Kim", "title": "Broker-Owner", "company": "Kim Properties", "email": "d.kim@kimprops.com", "score": 94},
        {"name": "Fatima Hassan", "title": "Team Lead", "company": "Hassan Group", "email": "f.hassan@hassan.com", "score": 90},
    ],
    "Won": [
        {"name": "Robert Liu", "title": "Managing Broker", "company": "Liu & Partners", "email": "r.liu@liupartners.com", "score": 97},
    ],
}


def get_leads_by_stage(stage: str, limit: int = 50) -> list[dict]:
    table = _get_table("Leads")
    if not table:
        return _STUB_LEADS_BY_STAGE.get(stage, [])

    try:
        records = table.all(formula=f"{{Stage}}='{stage}'")[:limit]
        return [
            {
                "name": r["fields"].get("Name", ""),
                "title": r["fields"].get("Title", ""),
                "company": r["fields"].get("Company", ""),
                "email": r["fields"].get("Email", ""),
                "score": r["fields"].get("Score", 0),
            }
            for r in records
        ]
    except Exception:
        return []
