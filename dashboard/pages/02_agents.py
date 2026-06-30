import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from orchestrator.router import dispatch
from orchestrator.state import get_last_run_per_agent
from dashboard.styles import apply_styles

st.set_page_config(page_title="Agents — BizOS", layout="wide")
apply_styles()

st.title("Agent Control Center")
st.caption("6 AI agents running your real estate SaaS business. All approval-gated before execution.")

AGENTS = [
    {
        "id": "lead_gen",
        "label": "LEADS",
        "name": "Lead Generation",
        "desc": "Finds and qualifies real estate professionals matching your ICP. Scores by company size, tech adoption, and social presence.",
        "schedule": "Daily at 07:00",
        "approval": "Required — adds leads to Airtable CRM",
        "payload": {"query": "Find 10 real estate agents and brokers in major US cities matching our ICP"},
    },
    {
        "id": "content",
        "label": "CONTENT",
        "name": "Content",
        "desc": "Researches RE industry news and generates platform-specific posts for LinkedIn, Twitter, and Instagram.",
        "schedule": "Mon / Wed / Fri at 08:00",
        "approval": "Required — schedules post via Buffer",
        "payload": {"platform": "LinkedIn", "content_type": "Market Update"},
    },
    {
        "id": "sales",
        "label": "SALES",
        "name": "Sales",
        "desc": "Pulls uncontacted leads from CRM and writes personalized outreach emails grounded in their context.",
        "schedule": "Weekdays at 09:00",
        "approval": "Required — creates Gmail draft",
        "payload": {},
    },
    {
        "id": "marketing",
        "label": "MARKETING",
        "name": "Marketing",
        "desc": "Analyzes RE industry trends and recommends weekly campaigns by channel with rationale and impact estimates.",
        "schedule": "Monday at 08:00",
        "approval": "Required — logs to Google Sheets",
        "payload": {"context": "Generate this week's marketing strategy for a real estate SaaS"},
    },
    {
        "id": "product",
        "label": "PRODUCT",
        "name": "Product Dev",
        "desc": "Clusters user feedback by theme, scores features by impact vs effort, and outputs a prioritized roadmap update.",
        "schedule": "Friday at 15:00",
        "approval": "Required — writes to Google Drive",
        "payload": {},
    },
    {
        "id": "operations",
        "label": "OPS",
        "name": "Operations",
        "desc": "Generates a terse daily CEO briefing from system stats, pending approvals, and calendar — pushes to Slack.",
        "schedule": "Daily at 06:00",
        "approval": "None — read-only, auto-sends to Slack",
        "payload": {},
    },
]

# Single DB query for all agents instead of N+1
last_runs = get_last_run_per_agent()

for agent in AGENTS:
    col_label, col_info, col_meta, col_run = st.columns([1, 4, 3, 1])

    with col_label:
        st.markdown(
            f"<div style='background:#407E3C;color:white;font-weight:700;"
            f"font-size:11px;letter-spacing:1px;padding:6px 10px;"
            f"border-radius:6px;text-align:center;margin-top:8px'>"
            f"{agent['label']}</div>",
            unsafe_allow_html=True,
        )

    with col_info:
        st.markdown(f"**{agent['name']} Agent**")
        st.caption(agent["desc"])

    with col_meta:
        last_run = last_runs.get(agent["id"], "Never")
        st.caption(f"Schedule: {agent['schedule']}")
        st.caption(f"Approval: {agent['approval']}")
        st.caption(f"Last run: {last_run}")

    with col_run:
        st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
        if st.button("Run", key=f"run_{agent['id']}"):
            with st.spinner(f"Running {agent['name']}..."):
                result = dispatch(agent["id"], "manual_trigger", agent["payload"])
            if result.get("status") == "awaiting_approval":
                st.success("Done — check Approvals")
            elif result.get("status") == "completed":
                st.success("Done")
            else:
                st.error(result.get("error", "Failed"))

    st.markdown("---")
