import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import pandas as pd
from tools.airtable_crm import get_crm_stats, get_uncontacted_leads

st.set_page_config(page_title="CRM — BizOS", layout="wide")
st.markdown("""
<style>
[data-testid="stSidebar"] { background: #407E3C !important; }
[data-testid="stSidebar"] * { color: white !important; }
h1, h2, h3 { color: #407E3C !important; }
.stButton > button { background: #407E3C !important; color: white !important; border: none !important; border-radius: 6px !important; }
</style>""", unsafe_allow_html=True)

st.title("📋 CRM — Lead Pipeline")

stats = get_crm_stats()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Leads", stats.get("total", 0))
with col2:
    by_stage = stats.get("by_stage", {})
    st.metric("New", by_stage.get("New", stats.get("new", 0)))
with col3:
    st.metric("Contacted", by_stage.get("Contacted", stats.get("contacted", 0)))
with col4:
    st.metric("Demo / Pipeline", by_stage.get("Demo Scheduled", stats.get("demo", 0)))

if stats.get("stub"):
    st.info("⚠️ Airtable not connected — showing demo data. Add AIRTABLE_API_KEY to .env to connect.")

st.markdown("---")
st.subheader("Uncontacted Leads")

leads = get_uncontacted_leads(limit=20)
if leads:
    df = pd.DataFrame(leads)
    display_cols = [c for c in ["name", "title", "company", "email", "notes"] if c in df.columns]
    st.dataframe(df[display_cols], use_container_width=True)

    st.caption("Run the Sales Agent to generate outreach emails for these leads.")
    if st.button("🚀 Run Sales Agent Now"):
        from orchestrator.router import dispatch
        with st.spinner("Sales agent running..."):
            result = dispatch("sales", "manual_trigger", {})
        if result.get("status") == "awaiting_approval":
            st.success("Email draft ready — check Approvals page to review and send.")
        else:
            st.error(result.get("error", "Unknown error"))
else:
    st.info("No uncontacted leads. Run the Lead Gen Agent to find new prospects.")

st.markdown("---")
st.subheader("Pipeline Stages")

stages = ["New", "Researched", "Contacted", "Replied", "Demo Scheduled", "Proposal Sent", "Won", "Lost"]
stage_data = stats.get("by_stage", {f: 0 for f in stages})

import plotly.graph_objects as go
fig = go.Figure(go.Funnel(
    y=stages,
    x=[stage_data.get(s, 0) for s in stages],
    textinfo="value+percent initial",
    marker=dict(color=["#407E3C", "#5a9e56", "#6dbf67", "#85cc80", "#9dd99a", "#b5e6b4", "#cef3cc", "#e8f5e9"]),
))
fig.update_layout(margin=dict(l=0, r=0, t=20, b=0), height=300)
st.plotly_chart(fig, use_container_width=True)
