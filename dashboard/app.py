import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
load_dotenv()

from orchestrator.state import init_db, get_stats, get_pending_approvals
from dashboard.styles import apply_styles

st.set_page_config(
    page_title="BizOS",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_styles()
init_db()

stats = get_stats()
pending_count = stats["pending_approvals"]

with st.sidebar:
    st.markdown(
        "<div style='font-size:20px;font-weight:800;letter-spacing:0.5px;"
        "padding:8px 0 2px 0'>BizOS</div>"
        "<div style='font-size:11px;color:rgba(255,255,255,0.65);margin-bottom:12px'>"
        "Real estate ops · AI-powered</div>",
        unsafe_allow_html=True,
    )

    @st.fragment(run_every=15)
    def _approval_notification():
        from orchestrator.state import get_stats
        n = get_stats()["pending_approvals"]
        if n > 0:
            st.markdown(
                f'<a class="notification-pulse" href="/01_Approvals" target="_self">'
                f'! {n} APPROVAL{"S" if n > 1 else ""} PENDING</a>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<span class="notification-clear">All approvals clear</span>',
                unsafe_allow_html=True,
            )

    _approval_notification()

    st.markdown(
        """
        <div class="nav-section">Overview</div>
        <a class="nav-link" href="/" target="_self">Command Center</a>

        <div class="nav-section">Operations</div>
        <a class="nav-link" href="/01_Approvals" target="_self">Approvals</a>
        <a class="nav-link" href="/02_Agents" target="_self">Agents</a>
        <a class="nav-link" href="/07_Workflows" target="_self">Workflows</a>
        <a class="nav-link" href="/08_Chat" target="_self">CEO Chat</a>

        <div class="nav-section">Data</div>
        <a class="nav-link" href="/03_Crm" target="_self">CRM</a>
        <a class="nav-link" href="/04_Content" target="_self">Content</a>
        <a class="nav-link" href="/05_Analytics" target="_self">Analytics</a>
        <a class="nav-link" href="/06_Memory" target="_self">Memory</a>
        """,
        unsafe_allow_html=True,
    )

st.title("BizOS — CEO Command Center")
st.caption("Real estate SaaS · AI-powered operations · Approval gates active")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Pending Approvals", pending_count)
with col2:
    st.metric("Total Tasks Run", stats["total_tasks"])
with col3:
    st.metric("Approved Today", stats["approved_today"])
with col4:
    st.metric("Active Agents", 6)

st.markdown("---")

pending_items = get_pending_approvals()
if pending_items:
    st.subheader(f"Pending Approvals  [{len(pending_items)}]")
    st.caption("Agents are waiting for your decision before executing.")

    for item in pending_items[:5]:
        preview = json.loads(item.get("preview_json", "{}"))
        agent_label = item["agent"].replace("_", " ").upper()
        action_label = item["action_type"].replace("_", " ").title()
        agent = item["agent"]

        with st.expander(
            f"{agent_label}  →  {action_label}   |   {item['created_at'][:16]}",
            expanded=True,
        ):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                if agent == "content" and preview.get("body"):
                    st.markdown(
                        f"**Platform:** {preview.get('platform', '')}  "
                        f"| **Type:** {preview.get('content_type', '')}"
                    )
                    if preview.get("hook"):
                        st.markdown(f"**Hook:** _{preview['hook']}_")
                    st.text_area("Draft", preview.get("body", ""), height=180, disabled=True, key=f"body_{item['id']}")
                    tags = " ".join(preview.get("hashtags", []))
                    if tags:
                        st.caption(f"Tags: {tags}")
                    if preview.get("suggested_publish_time"):
                        st.caption(f"Publish: {preview['suggested_publish_time']}")
                elif agent == "sales" and preview.get("body"):
                    st.markdown(f"**To:** {preview.get('to_name', '')} `<{preview.get('to', '')}>`")
                    st.markdown(f"**Subject:** {preview.get('subject', '')}")
                    if preview.get("personalization_used"):
                        st.caption("Personalization: " + ", ".join(preview["personalization_used"]))
                    st.text_area("Email", preview.get("body", ""), height=180, disabled=True, key=f"email_{item['id']}")
                elif agent == "lead_gen" and preview.get("leads"):
                    st.markdown(f"**{preview.get('lead_count', 0)} leads found**")
                    df = pd.DataFrame(preview["leads"])
                    show_cols = [c for c in ["name", "title", "company", "email", "score", "city", "state"] if c in df.columns]
                    st.dataframe(df[show_cols], use_container_width=True)
                elif agent == "marketing" and preview.get("recommendations"):
                    st.markdown(f"**Summary:** {preview.get('summary', '')}")
                    st.markdown(f"**Next week focus:** {preview.get('next_week_focus', '')}")
                    for rec in preview.get("recommendations", []):
                        st.markdown(
                            f"- **{rec.get('campaign', '')}** ({rec.get('channel', '')}) — "
                            f"{rec.get('rationale', '')}"
                        )
                elif agent == "product" and preview.get("top_features"):
                    st.markdown(f"**{preview.get('feature_count', 0)} features analyzed**")
                    st.markdown(f"**Next sprint:** {preview.get('next_sprint', '')}")
                    for feat in preview.get("top_features", []):
                        st.markdown(
                            f"- **{feat.get('title', '')}** "
                            f"(Impact {feat.get('impact')}/Effort {feat.get('effort')} "
                            f"= Priority {feat.get('priority_score', 0):.1f}) — "
                            f"{feat.get('recommendation', '')}"
                        )
                else:
                    st.json(preview)
            with col_b:
                st.markdown(f"**Will:** {preview.get('action', 'Execute action')}")
                feedback = st.text_area(
                    "Note (optional)", key=f"fb_{item['id']}", height=80
                )
                if st.button("Approve", key=f"approve_{item['id']}"):
                    from orchestrator.approval import approve
                    try:
                        result = approve(item["id"], feedback)
                        exec_result = result.get("execution", {})
                        if exec_result.get("error"):
                            st.warning(f"Approved but execution failed: {exec_result['error']}")
                        else:
                            st.success("Approved and executed.")
                    except ValueError as e:
                        st.error(str(e))
                    st.rerun()
                if st.button("Reject", key=f"reject_{item['id']}"):
                    if not feedback.strip():
                        st.warning("Add a note before rejecting.")
                    else:
                        from orchestrator.approval import reject
                        reject(item["id"], feedback)
                        st.warning("Rejected.")
                        st.rerun()
else:
    st.info("No pending approvals. All agents are idle or complete.")

st.markdown("---")
st.subheader("Quick Run")
st.caption("Trigger any agent manually right now.")

AGENTS = [
    ("lead_gen",    "Leads",      {"query": "Find 10 RE professionals matching our ICP"}),
    ("content",     "Content",    {"platform": "LinkedIn", "content_type": "Market Update"}),
    ("sales",       "Sales",      {}),
    ("marketing",   "Marketing",  {"context": "Generate this week's marketing strategy"}),
    ("product",     "Product",    {}),
    ("operations",  "Operations", {}),
]

agent_cols = st.columns(6)
for i, (agent_id, label, payload) in enumerate(AGENTS):
    with agent_cols[i]:
        if st.button(label, key=f"trigger_{agent_id}"):
            with st.spinner(f"Running {label}..."):
                from orchestrator.router import dispatch
                result = dispatch(agent_id, "manual_trigger", payload)
            if result.get("status") == "awaiting_approval":
                st.success("Done — review above.")
            elif result.get("status") == "completed":
                st.success("Done.")
            else:
                st.error(result.get("error", "Error"))
            st.rerun()
