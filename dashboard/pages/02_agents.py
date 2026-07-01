import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from orchestrator.router import get_agent, dispatch_with_agent
from orchestrator.state import get_last_run_per_agent, init_db
from dashboard.styles import apply_styles

st.set_page_config(page_title="Agents — BizOS", layout="wide")
apply_styles()
init_db()

st.title("Agent Control Center")
st.caption("6 AI agents running your real estate SaaS business. All approval-gated before execution.")

sched_log = Path(__file__).resolve().parents[2] / "data" / "scheduler.log"
if sched_log.exists():
    st.success("Scheduler running — agents fire automatically on schedule.")
else:
    st.info("Scheduler not running. Launch `python scheduler.py` to enable automatic agent runs.")

AGENTS = [
    {
        "id": "lead_gen",
        "label": "LEADS",
        "name": "Lead Generation",
        "desc": "Finds and qualifies real estate professionals matching your ICP. Scores by company size, tech adoption, and social presence.",
        "schedule": "Daily at 07:00",
        "approval": "Required — adds leads to Airtable CRM",
        "payload": {"query": "Find 10 real estate agents and brokers in major US cities matching our ICP"},
    },
    {
        "id": "content",
        "label": "CONTENT",
        "name": "Content",
        "desc": "Researches RE industry news and generates platform-specific posts for LinkedIn, Twitter, and Instagram.",
        "schedule": "Mon / Wed / Fri at 08:00",
        "approval": "Required — schedules post via Buffer",
        "payload": {"platform": "LinkedIn", "content_type": "Market Update"},
    },
    {
        "id": "sales",
        "label": "SALES",
        "name": "Sales",
        "desc": "Pulls uncontacted leads from CRM and writes personalized outreach emails grounded in their context.",
        "schedule": "Weekdays at 09:00",
        "approval": "Required — creates Gmail draft",
        "payload": {},
    },
    {
        "id": "marketing",
        "label": "MARKETING",
        "name": "Marketing",
        "desc": "Analyzes RE industry trends and recommends weekly campaigns by channel with rationale and impact estimates.",
        "schedule": "Monday at 08:00",
        "approval": "Required — logs to Google Sheets",
        "payload": {"context": "Generate this week's marketing strategy for a real estate SaaS"},
    },
    {
        "id": "product",
        "label": "PRODUCT",
        "name": "Product Dev",
        "desc": "Clusters user feedback by theme, scores features by impact vs effort, and outputs a prioritized roadmap update.",
        "schedule": "Friday at 15:00",
        "approval": "Required — writes to Google Drive",
        "payload": {},
    },
    {
        "id": "operations",
        "label": "OPS",
        "name": "Operations",
        "desc": "Generates a terse daily CEO briefing from system stats, pending approvals, and calendar — pushes to Slack.",
        "schedule": "Daily at 06:00",
        "approval": "None — read-only, auto-sends to Slack",
        "payload": {},
    },
]

last_runs = get_last_run_per_agent()

for agent_cfg in AGENTS:
    col_label, col_info, col_meta, col_run = st.columns([1, 4, 3, 1])

    with col_label:
        st.markdown(
            f"<div style='background:#407E3C;color:white;font-weight:700;"
            f"font-size:11px;letter-spacing:1px;padding:6px 10px;"
            f"border-radius:6px;text-align:center;margin-top:8px'>"
            f"{agent_cfg['label']}</div>",
            unsafe_allow_html=True,
        )

    with col_info:
        st.markdown(f"**{agent_cfg['name']} Agent**")
        st.caption(agent_cfg["desc"])

    with col_meta:
        last_run = last_runs.get(agent_cfg["id"], "Never")
        st.caption(f"Schedule: {agent_cfg['schedule']}")
        st.caption(f"Approval: {agent_cfg['approval']}")
        st.caption(f"Last run: {last_run}")

    with col_run:
        st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
        if st.button("Run", key=f"run_{agent_cfg['id']}"):
            agent_id = agent_cfg["id"]
            payload = agent_cfg["payload"]

            stream_placeholder = st.empty()
            status_placeholder = st.empty()
            chunks: list[str] = []

            def make_on_chunk(placeholder, buf):
                def on_chunk(delta: str):
                    buf.append(delta)
                    placeholder.markdown(
                        "<div style='font-size:13px;font-family:monospace;"
                        "background:#f8f8f8;padding:10px;border-radius:6px;"
                        "border-left:3px solid #407E3C;max-height:200px;overflow-y:auto'>"
                        + "".join(buf).replace("\n", "<br>")
                        + "▌</div>",
                        unsafe_allow_html=True,
                    )
                return on_chunk

            try:
                agent_instance = get_agent(agent_id)
                agent_instance._on_chunk = make_on_chunk(stream_placeholder, chunks)
                result = dispatch_with_agent(agent_instance, agent_id, "manual_trigger", payload)
            finally:
                # Clear streaming cursor, show final text
                if chunks:
                    stream_placeholder.markdown(
                        "<div style='font-size:13px;font-family:monospace;"
                        "background:#f8f8f8;padding:10px;border-radius:6px;"
                        "border-left:3px solid #407E3C;max-height:200px;overflow-y:auto'>"
                        + "".join(chunks).replace("\n", "<br>")
                        + "</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    stream_placeholder.empty()

            if result.get("status") == "awaiting_approval":
                status_placeholder.success("Done — check Approvals")
            elif result.get("status") == "completed":
                status_placeholder.success("Done")
            else:
                status_placeholder.error(result.get("error", "Failed"))

            st.rerun()

    st.markdown("---")
