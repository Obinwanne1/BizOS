import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json
import streamlit as st
import pandas as pd
from orchestrator.state import get_pending_approvals, get_agent_logs
from orchestrator.approval import approve, reject

st.set_page_config(page_title="Approvals — BizOS", layout="wide")
st.markdown("""
<style>
[data-testid="stSidebar"] { background: #407E3C !important; }
[data-testid="stSidebar"] * { color: white !important; }
h1, h2, h3 { color: #407E3C !important; }
.stButton > button {
    background: #407E3C !important; color: white !important;
    border: none !important; border-radius: 6px !important; font-weight: 600 !important;
}
.stButton > button:hover { background: #5a9e56 !important; }
</style>""", unsafe_allow_html=True)

st.title("Approval Queue")

tab_pending, tab_history = st.tabs(["Pending", "History"])

with tab_pending:
    pending = get_pending_approvals()
    if not pending:
        st.success("All clear — no pending approvals.")
    else:
        st.caption(f"{len(pending)} item(s) waiting for review.")
        for item in pending:
            preview = json.loads(item.get("preview_json", "{}"))
            agent_label = item["agent"].replace("_", " ").upper()
            action_label = item["action_type"].replace("_", " ").title()

            with st.container():
                st.markdown(f"### {agent_label}  →  {action_label}")
                st.caption(f"Queued: {item['created_at'][:16]}")

                col_preview, col_actions = st.columns([3, 1])

                with col_preview:
                    agent = item["agent"]
                    if agent == "content" and preview.get("body"):
                        st.markdown(
                            f"**Platform:** {preview.get('platform', '')}  "
                            f"| **Type:** {preview.get('content_type', '')}"
                        )
                        if preview.get("hook"):
                            st.markdown(f"**Hook:** _{preview['hook']}_")
                        st.text_area(
                            "Draft", preview.get("body", ""),
                            height=220, disabled=True, key=f"body_{item['id']}"
                        )
                        tags = " ".join(preview.get("hashtags", []))
                        if tags:
                            st.caption(f"Tags: {tags}")
                        if preview.get("suggested_publish_time"):
                            st.caption(f"Publish: {preview['suggested_publish_time']}")

                    elif agent == "sales" and preview.get("body"):
                        st.markdown(
                            f"**To:** {preview.get('to_name', '')} "
                            f"`<{preview.get('to', '')}>`"
                        )
                        st.markdown(f"**Subject:** {preview.get('subject', '')}")
                        if preview.get("personalization_used"):
                            st.caption("Personalization: " + ", ".join(preview["personalization_used"]))
                        st.text_area(
                            "Email", preview.get("body", ""),
                            height=220, disabled=True, key=f"email_{item['id']}"
                        )

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

                with col_actions:
                    st.markdown(f"**Will:** {preview.get('action', 'Execute action')}")
                    feedback = st.text_area(
                        "Note", key=f"fb_{item['id']}",
                        height=70, placeholder="Optional context..."
                    )
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Approve", key=f"app_{item['id']}"):
                            try:
                                approve(item["id"], feedback)
                                st.success("Approved")
                                st.rerun()
                            except ValueError as e:
                                st.error(str(e))
                    with c2:
                        if st.button("Reject", key=f"rej_{item['id']}"):
                            if not feedback.strip():
                                st.warning("Add a note before rejecting.")
                            else:
                                reject(item["id"], feedback)
                                st.warning("Rejected")
                                st.rerun()

                st.markdown("---")

with tab_history:
    logs = get_agent_logs(limit=50)
    if logs:
        df = pd.DataFrame(logs)
        df = df[["agent", "action", "approved_by", "timestamp"]].copy()
        df.columns = ["Agent", "Action", "By", "Time"]
        df["Agent"] = df["Agent"].str.replace("_", " ").str.upper()
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No history yet.")
