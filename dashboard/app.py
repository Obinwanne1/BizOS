import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
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
    st.markdown("## BizOS")
    st.markdown("*Real estate operations, automated*")
    st.markdown("---")
    if pending_count > 0:
        st.markdown(
            f'<span class="alert-badge">! {pending_count} PENDING</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown("All approvals clear")
    st.markdown("---")
    st.caption("Navigate using the pages above.")

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

        with st.expander(
            f"{agent_label}  →  {action_label}   |   {item['created_at'][:16]}",
            expanded=True,
        ):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.json(preview)
            with col_b:
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
