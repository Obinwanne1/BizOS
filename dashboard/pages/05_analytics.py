import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import pandas as pd
import plotly.express as px
from orchestrator.state import get_agent_logs, get_stats
from tools.airtable_crm import get_crm_stats

st.set_page_config(page_title="Analytics — BizOS", layout="wide")
st.markdown("""
<style>
[data-testid="stSidebar"] { background: #407E3C !important; }
[data-testid="stSidebar"] * { color: white !important; }
h1, h2, h3 { color: #407E3C !important; }
</style>""", unsafe_allow_html=True)

st.title("📊 Analytics & KPIs")

stats = get_stats()
crm = get_crm_stats()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Leads in CRM", crm.get("total", 0))
with col2:
    st.metric("Total Agent Tasks", stats["total_tasks"])
with col3:
    st.metric("Actions Approved", stats["approved_today"], delta="today")
with col4:
    st.metric("Pending Review", stats["pending_approvals"])

st.markdown("---")

logs = get_agent_logs(limit=100)
if logs:
    df = pd.DataFrame(logs)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["date"] = df["timestamp"].dt.date

    st.subheader("Agent Activity by Type")
    agent_counts = df.groupby("agent").size().reset_index(name="count")
    fig = px.bar(
        agent_counts, x="agent", y="count",
        color_discrete_sequence=["#407E3C"],
        labels={"agent": "Agent", "count": "Actions"},
    )
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Activity Over Time")
    daily = df.groupby("date").size().reset_index(name="actions")
    fig2 = px.line(
        daily, x="date", y="actions",
        color_discrete_sequence=["#407E3C"],
        markers=True,
    )
    fig2.update_layout(margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Recent Activity Log")
    display = df[["agent", "action", "approved_by", "timestamp"]].copy()
    display.columns = ["Agent", "Action", "Approved By", "Time"]
    display["Time"] = display["Time"].dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(display.head(20), use_container_width=True)
else:
    st.info("No agent activity yet. Trigger agents from the Agents page to see analytics.")
