import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
from orchestrator.router import dispatch
from orchestrator.state import get_agent_logs

st.set_page_config(page_title="Agents — BizOS", layout="wide")
st.markdown("""
<style>
[data-testid="stSidebar"] { background: #407E3C !important; }
[data-testid="stSidebar"] * { color: white !important; }
h1, h2, h3 { color: #407E3C !important; }
.stButton > button { background: #407E3C !important; color: white !important; border: none !important; border-radius: 6px !important; }
.agent-card { background: white; border: 1px solid #e8f5e9; border-radius: 10px; padding: 16px; margin-bottom: 12px; }
</style>""", unsafe_allow_html=True)

st.title("⚡ Agent Control Center")

AGENTS = [
    {
        "id": "lead_gen",
        "name": "Lead Gen Agent",
        "icon": "🔍",
        "desc": "Finds and qualifies real estate professionals matching your ICP",
        "schedule": "Daily 7:00 AM",
        "trigger_payload": {"query": "Find 10 real estate agents and brokers in major US cities matching our ICP"},
    },
    {
        "id": "content",
        "name": "Content Agent",
        "icon": "✍️",
        "desc": "Generates RE industry content for LinkedIn, Twitter, and Instagram",
        "schedule": "Mon/Wed/Fri 8:00 AM",
        "trigger_payload": {"platform": "LinkedIn", "content_type": "Market Update"},
    },
    {
        "id": "sales",
        "name": "Sales Agent",
        "icon": "📧",
        "desc": "Writes personalized outreach emails for uncontacted CRM leads",
        "schedule": "Daily 9:00 AM (weekdays)",
        "trigger_payload": {},
    },
    {
        "id": "marketing",
        "name": "Marketing Agent",
        "icon": "📊",
        "desc": "Analyzes performance and recommends weekly campaigns",
        "schedule": "Monday 8:00 AM",
        "trigger_payload": {"context": "Generate this week's marketing strategy"},
    },
    {
        "id": "product",
        "name": "Product Dev Agent",
        "icon": "🛠",
        "desc": "Triages user feedback and updates the product roadmap",
        "schedule": "Friday 3:00 PM",
        "trigger_payload": {},
    },
    {
        "id": "operations",
        "name": "Operations Agent",
        "icon": "⚙️",
        "desc": "Generates daily CEO briefing and sends to Slack",
        "schedule": "Daily 6:00 AM",
        "trigger_payload": {},
    },
]

for agent in AGENTS:
    with st.container():
        col_info, col_trigger = st.columns([4, 1])
        with col_info:
            st.markdown(f"### {agent['icon']} {agent['name']}")
            st.caption(agent["desc"])
            st.caption(f"🕐 Schedule: {agent['schedule']}")
            logs = get_agent_logs(agent["id"], limit=1)
            if logs:
                st.caption(f"Last run: {logs[0]['timestamp'][:16]} — {logs[0]['action']}")
        with col_trigger:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(f"Run Now", key=f"run_{agent['id']}"):
                with st.spinner(f"Running {agent['name']}..."):
                    result = dispatch(agent["id"], "manual_trigger", agent["trigger_payload"])
                if result.get("status") == "awaiting_approval":
                    st.success("✅ Done — check Approvals page")
                elif result.get("status") == "completed":
                    st.success("✅ Completed")
                else:
                    st.error(f"Error: {result.get('error', 'Unknown')}")
        st.markdown("---")
