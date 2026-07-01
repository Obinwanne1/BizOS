import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import pandas as pd
import plotly.express as px
from orchestrator.state import get_agent_logs, get_stats
from tools.airtable_crm import get_crm_stats
from dashboard.styles import apply_styles

st.set_page_config(page_title="Analytics — BizOS", layout="wide")
apply_styles()


@st.cache_data(ttl=60)
def _logs(limit=200):
    return get_agent_logs(limit=limit)


@st.cache_data(ttl=30)
def _stats():
    return get_stats()


@st.cache_data(ttl=300)
def _crm():
    return get_crm_stats()


st.title("Analytics")

stats = _stats()
crm = _crm()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Leads", crm.get("total", 0))
with col2:
    st.metric("Agent Tasks Run", stats["total_tasks"])
with col3:
    st.metric("Approved Today", stats["approved_today"])
with col4:
    st.metric("Pending Review", stats["pending_approvals"])

st.markdown("---")

logs = _logs(200)
if not logs:
    st.info("No agent activity yet. Trigger agents from the Agents page.")
    st.stop()

df = pd.DataFrame(logs)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["date"] = df["timestamp"].dt.date
df["agent_label"] = df["agent"].str.replace("_", " ").str.upper()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Activity by Agent")
    counts = df.groupby("agent_label").size().reset_index(name="Tasks")
    fig = px.bar(
        counts, x="agent_label", y="Tasks",
        color_discrete_sequence=["#407E3C"],
        labels={"agent_label": "Agent"},
    )
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Daily Activity")
    daily = df.groupby("date").size().reset_index(name="Tasks")
    fig2 = px.line(
        daily, x="date", y="Tasks",
        color_discrete_sequence=["#407E3C"],
        markers=True,
    )
    fig2.update_layout(margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig2, use_container_width=True)

st.subheader("Recent Activity Log")
display = df[["agent_label", "action", "approved_by", "timestamp"]].copy()
display.columns = ["Agent", "Action", "By", "Time"]
display["Time"] = display["Time"].dt.strftime("%Y-%m-%d %H:%M")
st.dataframe(display.head(30), use_container_width=True)
