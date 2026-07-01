import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from tools.airtable_crm import get_crm_stats, get_uncontacted_leads, get_leads_by_stage
from dashboard.styles import apply_styles

st.set_page_config(page_title="CRM — BizOS", layout="wide")
apply_styles()

st.title("CRM — Lead Pipeline")

stats = get_crm_stats()

if stats.get("stub"):
    st.warning(
        "Airtable not connected — showing demo data. "
        "Add AIRTABLE_API_KEY and AIRTABLE_BASE_ID to .env to connect."
    )

col1, col2, col3, col4 = st.columns(4)
by_stage = stats.get("by_stage", {})
with col1:
    st.metric("Total Leads", stats.get("total", 0))
with col2:
    st.metric("New", by_stage.get("New", stats.get("new", 0)))
with col3:
    st.metric("Contacted", by_stage.get("Contacted", stats.get("contacted", 0)))
with col4:
    st.metric("In Pipeline", by_stage.get("Demo Scheduled", stats.get("demo", 0)))

st.markdown("---")
st.subheader("Uncontacted Leads")

leads = get_uncontacted_leads(limit=20)
if leads:
    df = pd.DataFrame(leads)
    show_cols = [c for c in ["name", "title", "company", "email", "score", "notes"] if c in df.columns]
    st.dataframe(df[show_cols], use_container_width=True)

    col_a, col_b = st.columns([3, 1])
    with col_b:
        if st.button("Run Sales Agent"):
            from orchestrator.router import dispatch
            with st.spinner("Drafting outreach email..."):
                result = dispatch("sales", "manual_trigger", {})
            if result.get("status") == "awaiting_approval":
                st.success("Email draft ready — check Approvals.")
            elif result.get("status") == "failed":
                st.error(result.get("error", "Failed"))
            else:
                st.info(result.get("status", "Done"))
else:
    st.markdown(
        """<div class="empty-state">
        <div class="empty-icon">[--]</div>
        <div class="empty-title">No uncontacted leads</div>
        <div class="empty-sub">Run Lead Gen to discover new prospects.</div>
        </div>""",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    if st.button("Run Lead Gen Agent"):
        from orchestrator.router import dispatch
        with st.spinner("Finding leads..."):
            result = dispatch("lead_gen", "manual_trigger", {
                "query": "Find 10 qualified RE professionals matching our ICP"
            })
        if result.get("status") == "awaiting_approval":
            st.success("Leads found — check Approvals to add to CRM.")
        else:
            st.error(result.get("error", "Failed"))

st.markdown("---")
st.subheader("Pipeline Funnel")
st.caption("Click a stage to drill down into leads at that stage.")

STAGES = ["New", "Researched", "Contacted", "Replied", "Demo Scheduled", "Proposal Sent", "Won", "Lost"]
counts = [by_stage.get(s, 0) for s in STAGES]

fig = go.Figure(go.Funnel(
    y=STAGES,
    x=counts,
    textinfo="value+percent initial",
    marker=dict(color=[
        "#407E3C", "#5a9e56", "#6dbf67", "#85cc80",
        "#9dd99a", "#b5e6b4", "#cef3cc", "#e8f5e9"
    ]),
    hovertemplate="<b>%{y}</b><br>%{x} leads<br>%{percentInitial} of total<extra></extra>",
))
fig.update_layout(
    margin=dict(l=0, r=0, t=10, b=0),
    height=300,
    clickmode="event+select",
)

event = st.plotly_chart(
    fig,
    use_container_width=True,
    on_select="rerun",
    selection_mode="points",
    key="funnel_chart",
)

# Drill-down: show leads for selected stage
if event and event.get("selection") and event["selection"].get("points"):
    pt = event["selection"]["points"][0]
    # Funnel point_index maps to STAGES list
    idx = pt.get("pointIndex", pt.get("point_index", None))
    if idx is not None and 0 <= idx < len(STAGES):
        selected_stage = STAGES[idx]
        stage_leads = get_leads_by_stage(selected_stage)
        st.markdown(f"#### {selected_stage} — {len(stage_leads)} lead(s)")
        if stage_leads:
            sdf = pd.DataFrame(stage_leads)
            show = [c for c in ["name", "title", "company", "email", "score"] if c in sdf.columns]
            st.dataframe(sdf[show], use_container_width=True)
        else:
            st.info(f"No leads in {selected_stage} stage.")
