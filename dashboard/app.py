import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from orchestrator.state import init_db, get_stats, get_pending_approvals

st.set_page_config(
    page_title="BizOS — CEO Dashboard",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
:root {
    --primary: #407E3C;
    --accent: #5a9e56;
    --bg-card: #f8fdf8;
}
[data-testid="stSidebar"] {
    background: #407E3C !important;
}
[data-testid="stSidebar"] * {
    color: white !important;
}
[data-testid="stSidebar"] .stRadio label { color: white !important; }
.metric-card {
    background: white;
    border-left: 4px solid #407E3C;
    padding: 16px 20px;
    border-radius: 8px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}
.agent-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
}
.badge-idle { background: #e8f5e9; color: #2e7d32; }
.badge-running { background: #fff3e0; color: #e65100; }
.badge-waiting { background: #e3f2fd; color: #1565c0; }
h1, h2, h3 { color: #407E3C !important; }
.stButton > button {
    background: #407E3C !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
}
.stButton > button:hover {
    background: #5a9e56 !important;
}
</style>
""", unsafe_allow_html=True)

init_db()

with st.sidebar:
    st.markdown("## 🏢 BizOS")
    st.markdown("*Run your business like a CEO*")
    st.markdown("---")

    stats = get_stats()
    pending = stats["pending_approvals"]

    if pending > 0:
        st.markdown(f"🔔 **{pending} pending approval{'s' if pending > 1 else ''}**")
    else:
        st.markdown("✅ No pending approvals")

    st.markdown("---")
    st.markdown("### Navigate")

st.title("BizOS — CEO Dashboard")
st.caption("Your AI business operating system for real estate SaaS")

stats = get_stats()
pending_items = get_pending_approvals()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Pending Approvals", stats["pending_approvals"], delta=None)
with col2:
    st.metric("Total Tasks Run", stats["total_tasks"])
with col3:
    st.metric("Approved Today", stats["approved_today"])
with col4:
    st.metric("Agents", "6", delta=None)

st.markdown("---")

if pending_items:
    st.subheader(f"🔔 Pending Approvals ({len(pending_items)})")
    st.caption("Review and approve agent actions before they execute.")

    for item in pending_items[:5]:
        import json
        preview = json.loads(item["preview_json"]) if item.get("preview_json") else {}

        with st.expander(
            f"**{item['agent'].replace('_', ' ').title()}** → {item['action_type'].replace('_', ' ').title()}  |  {item['created_at'][:16]}",
            expanded=True,
        ):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.json(preview)
            with col_b:
                feedback = st.text_area("Feedback (optional)", key=f"fb_{item['id']}", height=80)
                if st.button("✅ Approve", key=f"approve_{item['id']}"):
                    from orchestrator.approval import approve
                    result = approve(item["id"], feedback)
                    st.success("Approved and executed.")
                    st.rerun()
                if st.button("❌ Reject", key=f"reject_{item['id']}"):
                    from orchestrator.approval import reject
                    reject(item["id"], feedback)
                    st.warning("Rejected.")
                    st.rerun()
else:
    st.info("No pending approvals. Agents are idle or all actions are complete.")

st.markdown("---")
st.subheader("⚡ Quick Trigger")
st.caption("Manually fire any agent right now.")

agent_cols = st.columns(6)
agents = ["lead_gen", "content", "sales", "marketing", "product", "operations"]
labels = ["🔍 Lead Gen", "✍️ Content", "📧 Sales", "📊 Marketing", "🛠 Product", "⚙️ Ops"]

for i, (agent, label) in enumerate(zip(agents, labels)):
    with agent_cols[i]:
        if st.button(label, key=f"trigger_{agent}"):
            with st.spinner(f"Running {agent}..."):
                from orchestrator.router import dispatch
                result = dispatch(agent, "manual_trigger", {})
                if result.get("status") == "awaiting_approval":
                    st.success("Done — check approvals above.")
                elif result.get("status") == "completed":
                    st.success("Completed.")
                else:
                    st.error(result.get("error", "Unknown error"))
            st.rerun()
