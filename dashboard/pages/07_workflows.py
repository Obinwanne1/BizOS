import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
load_dotenv()

import json
import streamlit as st
from orchestrator.workflow import WORKFLOWS, run_workflow
from orchestrator.state import get_workflow_runs, init_db
from dashboard.styles import apply_styles

st.set_page_config(page_title="Workflows — BizOS", layout="wide")
apply_styles()
init_db()

st.title("Workflow Orchestration")
st.caption("Multi-agent pipelines. One click runs a full sequence of agents end-to-end.")

tab_run, tab_history = st.tabs(["Run Workflows", "Run History"])

with tab_run:
    for wf_name, wf in WORKFLOWS.items():
        steps = wf["steps"]
        with st.container():
            col_info, col_steps, col_btn = st.columns([3, 4, 1])

            with col_info:
                st.markdown(f"#### {wf['name']}")
                st.caption(wf["description"])

            with col_steps:
                step_labels = " → ".join(
                    f"**{s['agent'].replace('_', ' ').upper()}**" for s in steps
                )
                st.markdown(step_labels)
                approval_count = sum(
                    1 for s in steps
                    if s["agent"] not in ("operations",)
                )
                st.caption(f"{len(steps)} steps · up to {approval_count} approval gate(s)")

            with col_btn:
                st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)
                if st.button("Run", key=f"wf_{wf_name}", type="primary"):
                    with st.spinner(f"Running {wf['name']}..."):
                        result = run_workflow(wf_name)

                    if result.get("error"):
                        st.error(result["error"])
                    else:
                        completed = result["steps_completed"]
                        pending = result["steps_pending_approval"]
                        failed = result["steps_failed"]
                        total = result["steps_total"]

                        if failed == 0 and pending > 0:
                            st.success(f"Done — {completed}/{total} completed, {pending} awaiting approval.")
                        elif failed == 0:
                            st.success(f"All {total} steps completed.")
                        else:
                            st.warning(f"{completed} completed, {pending} pending, {failed} failed.")

                        with st.expander("Step details", expanded=False):
                            for step in result.get("step_results", []):
                                status = step["status"]
                                icon = "[ok]" if status == "completed" else ("[..] " if status == "awaiting_approval" else "[!]")
                                st.markdown(
                                    f"`{icon}` Step {step['step']} — **{step['agent'].upper()}** — `{status}`"
                                    + (f" · approval_id: `{step['approval_id'][:8]}…`" if step.get("approval_id") else "")
                                    + (f" · error: {step['error']}" if step.get("error") else "")
                                )
                        st.rerun()

            st.markdown("---")

with tab_history:
    runs = get_workflow_runs(limit=30)
    if not runs:
        st.info("No workflows run yet.")
    else:
        for run in runs:
            step_results = json.loads(run.get("step_results_json", "[]"))
            completed = sum(1 for s in step_results if s.get("status") == "completed")
            pending = sum(1 for s in step_results if s.get("status") == "awaiting_approval")
            total = len(step_results)
            status = run["status"]
            status_color = {"completed": "#407E3C", "partial": "#e0a000", "failed": "#cc0000", "running": "#888"}.get(status, "#888")

            with st.expander(
                f"{run['workflow_name'].replace('_', ' ').title()}  ·  {run['started_at'][:16]}",
                expanded=False,
            ):
                col_s, col_d = st.columns([1, 3])
                with col_s:
                    st.markdown(
                        f"<span style='color:{status_color};font-weight:700'>{status.upper()}</span>",
                        unsafe_allow_html=True,
                    )
                    st.caption(f"Run ID: {run['id'][:8]}…")
                    if run.get("completed_at"):
                        st.caption(f"Finished: {run['completed_at'][:16]}")
                with col_d:
                    for step in step_results:
                        s_status = step.get("status", "?")
                        icon = "[ok]" if s_status == "completed" else ("[..] " if s_status == "awaiting_approval" else "[!]")
                        st.markdown(
                            f"`{icon}` Step {step['step']} — **{step.get('agent','?').upper()}** — `{s_status}`"
                        )
