import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import json
import streamlit as st
from orchestrator.state import get_pending_approvals, get_agent_logs
from orchestrator.approval import approve, reject

st.set_page_config(page_title="Approvals — BizOS", layout="wide")
st.markdown("""
<style>
[data-testid="stSidebar"] { background: #407E3C !important; }
[data-testid="stSidebar"] * { color: white !important; }
h1, h2, h3 { color: #407E3C !important; }
.stButton > button { background: #407E3C !important; color: white !important; border: none !important; border-radius: 6px !important; }
</style>""", unsafe_allow_html=True)

st.title("🔔 Approval Queue")

tab1, tab2 = st.tabs(["Pending", "History"])

with tab1:
    pending = get_pending_approvals()
    if not pending:
        st.success("All clear — no pending approvals.")
    else:
        st.caption(f"{len(pending)} item(s) waiting for your review.")
        for item in pending:
            preview = json.loads(item.get("preview_json", "{}"))
            agent_name = item["agent"].replace("_", " ").title()
            action = item["action_type"].replace("_", " ").title()

            with st.container():
                st.markdown(f"### {agent_name} → {action}")
                st.caption(f"Queued: {item['created_at'][:16]}")

                agent_icon = {
                    "lead_gen": "🔍", "content": "✍️", "sales": "📧",
                    "marketing": "📊", "product": "🛠", "operations": "⚙️",
                }.get(item["agent"], "🤖")

                col_preview, col_actions = st.columns([3, 1])
                with col_preview:
                    if item["agent"] == "content" and "body" in preview:
                        st.markdown(f"**Platform:** {preview.get('platform', '')} | **Type:** {preview.get('content_type', '')}")
                        st.markdown(f"**Hook:** {preview.get('hook', '')}")
                        st.text_area("Content Body", preview.get("body", ""), height=200, disabled=True, key=f"body_{item['id']}")
                        st.markdown(f"**Hashtags:** {' '.join(preview.get('hashtags', []))}")
                        st.markdown(f"**Publish:** {preview.get('suggested_publish_time', 'ASAP')}")
                    elif item["agent"] == "sales" and "body" in preview:
                        st.markdown(f"**To:** {preview.get('to_name', '')} <{preview.get('to', '')}>")
                        st.markdown(f"**Subject:** {preview.get('subject', '')}")
                        st.text_area("Email Body", preview.get("body", ""), height=200, disabled=True, key=f"email_{item['id']}")
                    elif item["agent"] == "lead_gen" and "leads" in preview:
                        st.markdown(f"**{preview.get('lead_count', 0)} leads found**")
                        import pandas as pd
                        leads_df = pd.DataFrame(preview.get("leads", []))
                        if not leads_df.empty:
                            st.dataframe(leads_df, use_container_width=True)
                    else:
                        st.json(preview)

                with col_actions:
                    st.markdown(f"**Action:** {preview.get('action', 'Execute')}")
                    feedback = st.text_area("Feedback", key=f"fb_{item['id']}", height=60, placeholder="Optional note...")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅", key=f"app_{item['id']}", help="Approve"):
                            approve(item["id"], feedback)
                            st.success("Approved!")
                            st.rerun()
                    with c2:
                        if st.button("❌", key=f"rej_{item['id']}", help="Reject"):
                            if not feedback:
                                st.warning("Add feedback before rejecting.")
                            else:
                                reject(item["id"], feedback)
                                st.warning("Rejected.")
                                st.rerun()
                st.markdown("---")

with tab2:
    logs = get_agent_logs(limit=30)
    if logs:
        import pandas as pd
        df = pd.DataFrame(logs)[["agent", "action", "approved_by", "timestamp"]]
        df.columns = ["Agent", "Action", "Approved By", "Time"]
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No history yet.")
