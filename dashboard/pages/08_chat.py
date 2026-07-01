import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
load_dotenv()

import json
import streamlit as st
import streamlit.components.v1 as components
from orchestrator.state import init_db
from orchestrator.router import get_agent, dispatch_with_agent
from dashboard.styles import apply_styles

st.set_page_config(page_title="Chat — BizOS", layout="wide")
apply_styles()
init_db()

# ── Session state ──────────────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "voice_prefill" not in st.session_state:
    st.session_state.voice_prefill = ""

# ── Page header ────────────────────────────────────────────────────────────────
st.title("CEO Chat")
st.caption("Talk to your AI OS. Natural language → agents → results.")

# ── Sidebar: voice input component ────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Voice Input")
    st.caption("Click mic, speak, then copy transcript to chat.")

    VOICE_HTML = """
    <style>
      body { margin: 0; font-family: sans-serif; }
      #mic { background: #407E3C; color: white; border: none; border-radius: 8px;
             padding: 10px 18px; font-size: 14px; cursor: pointer; width: 100%; }
      #mic:active { background: #cc0000; }
      #status { font-size: 12px; color: #555; margin-top: 8px; }
      #transcript { font-size: 13px; font-weight: bold; color: #222;
                    margin-top: 6px; word-break: break-word; min-height: 24px; }
    </style>
    <button id="mic" onclick="startListen()">[MIC] Click to speak</button>
    <div id="status">Ready.</div>
    <div id="transcript"></div>
    <script>
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      document.getElementById('status').textContent = 'Speech not supported in this browser.';
      document.getElementById('mic').disabled = true;
    }
    function startListen() {
      const rec = new SpeechRec();
      rec.lang = 'en-US';
      rec.continuous = false;
      rec.interimResults = false;
      document.getElementById('mic').textContent = '[REC] Listening...';
      document.getElementById('status').textContent = 'Speak now...';
      rec.start();
      rec.onresult = (e) => {
        const t = e.results[0][0].transcript;
        document.getElementById('transcript').textContent = '> ' + t;
        document.getElementById('status').textContent = 'Done. Copy text above to chat.';
        document.getElementById('mic').textContent = '[MIC] Click to speak';
      };
      rec.onerror = (e) => {
        document.getElementById('status').textContent = 'Error: ' + e.error;
        document.getElementById('mic').textContent = '[MIC] Click to speak';
      };
      rec.onend = () => {
        document.getElementById('mic').textContent = '[MIC] Click to speak';
      };
    }
    </script>
    """
    components.html(VOICE_HTML, height=140)

    st.markdown("---")
    st.markdown("### Quick Actions")
    quick_actions = [
        ("Find leads",      "Find 10 qualified real estate leads matching our ICP"),
        ("Write content",   "Write a LinkedIn post about real estate market trends"),
        ("Ops briefing",    "Give me today's operations briefing"),
        ("Marketing plan",  "Generate this week's marketing strategy"),
        ("Pipeline sprint", "Run the full pipeline and marketing sprint"),
    ]
    for label, prompt in quick_actions:
        if st.button(label, key=f"quick_{label}", use_container_width=True):
            st.session_state.voice_prefill = prompt
            st.rerun()

    if st.button("Clear history", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

# ── Chat history display ───────────────────────────────────────────────────────
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("status_badge"):
            badge_color = "#407E3C" if "approval" in msg["status_badge"] else "#555"
            st.markdown(
                f"<span style='font-size:11px;color:{badge_color};font-weight:700'>"
                f"{msg['status_badge']}</span>",
                unsafe_allow_html=True,
            )

# ── Chat input ─────────────────────────────────────────────────────────────────
prefill = st.session_state.pop("voice_prefill", "") if st.session_state.get("voice_prefill") else ""

user_input = st.chat_input("Tell your AI OS what to do…")

# Allow quick-action prefill to submit automatically
if prefill and not user_input:
    user_input = prefill

if user_input:
    # Add user message to history
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # ── Route + respond ────────────────────────────────────────────────────────
    with st.chat_message("assistant"):
        # Step 1: orchestrate — determine workflow vs agent
        routing_placeholder = st.empty()
        routing_placeholder.caption("Routing intent…")

        try:
            from agents.orchestrator import OrchestratorAgent
            orch = OrchestratorAgent()
            orch_result = orch.run({"intent": user_input})
            plan = orch_result.output.get("plan", {}) if not orch_result.error else {}
        except Exception as e:
            plan = {}
            routing_placeholder.warning(f"Routing failed: {e}")

        action = plan.get("action", "dispatch_agent")
        reasoning = plan.get("reasoning", "")

        if reasoning:
            routing_placeholder.caption(f"*{reasoning}*")
        else:
            routing_placeholder.empty()

        # Step 2: execute
        if action == "run_workflow":
            wf_name = plan.get("workflow", "")
            from orchestrator.workflow import WORKFLOWS, run_workflow
            if wf_name not in WORKFLOWS:
                st.error(f"Unknown workflow: {wf_name!r}")
                reply = f"Could not find workflow `{wf_name}`."
                badge = "error"
            else:
                wf_info = WORKFLOWS[wf_name]
                with st.spinner(f"Running workflow: {wf_info['name']}…"):
                    wf_result = run_workflow(wf_name, plan.get("payload"))

                completed = wf_result["steps_completed"]
                pending = wf_result["steps_pending_approval"]
                total = wf_result["steps_total"]
                failed = wf_result["steps_failed"]

                step_lines = []
                for s in wf_result.get("step_results", []):
                    icon = "[ok]" if s["status"] == "completed" else ("[..] " if s["status"] == "awaiting_approval" else "[!]")
                    step_lines.append(f"{icon} {s['agent'].upper()} — {s['status']}")

                reply = (
                    f"**{wf_info['name']}** complete.\n\n"
                    + "\n".join(step_lines)
                    + f"\n\n{completed}/{total} completed"
                    + (f", {pending} awaiting approval" if pending else "")
                    + (f", {failed} failed" if failed else "")
                    + "."
                )
                badge = f"{pending} approval(s) pending" if pending else f"{completed}/{total} steps done"
                st.markdown(reply)
                if pending:
                    st.info("Go to **Approvals** page to review.")

        else:
            # Single agent dispatch with streaming
            agent_name = plan.get("agent", "operations")
            agent_payload = plan.get("payload", {})

            # Map natural-language task to agent default payload if payload is empty
            AGENT_DEFAULT_PAYLOAD = {
                "lead_gen": {"query": user_input},
                "content": {"platform": "LinkedIn", "content_type": "Market Update"},
                "sales": {},
                "marketing": {"context": user_input},
                "product": {},
                "operations": {},
            }
            if not agent_payload:
                agent_payload = AGENT_DEFAULT_PAYLOAD.get(agent_name, {})

            stream_box = st.empty()
            chunks: list[str] = []

            def _on_chunk(delta: str, _box=stream_box, _buf=chunks):
                _buf.append(delta)
                _box.markdown(
                    "<div style='font-size:13px;font-family:monospace;"
                    "background:#f8f8f8;padding:10px;border-radius:6px;"
                    "border-left:3px solid #407E3C'>"
                    + "".join(_buf).replace("\n", "<br>")
                    + "▌</div>",
                    unsafe_allow_html=True,
                )

            result = {"status": "failed", "error": "Agent not started"}
            try:
                agent_instance = get_agent(agent_name)
                agent_instance._on_chunk = _on_chunk
                result = dispatch_with_agent(agent_instance, agent_name, "chat", agent_payload)
            except Exception as e:
                result = {"status": "failed", "error": str(e)}

            # Finalize stream display
            final_text = "".join(chunks)
            if final_text:
                stream_box.markdown(
                    "<div style='font-size:13px;font-family:monospace;"
                    "background:#f8f8f8;padding:10px;border-radius:6px;"
                    "border-left:3px solid #407E3C'>"
                    + final_text.replace("\n", "<br>")
                    + "</div>",
                    unsafe_allow_html=True,
                )
            else:
                stream_box.empty()

            status = result.get("status", "failed")
            if status == "awaiting_approval":
                badge = "Awaiting approval"
                reply = f"*{agent_name.upper()} agent* queued an action for your approval."
                st.info("Go to **Approvals** page to review.")
            elif status == "completed":
                badge = f"{agent_name.upper()} done"
                reply = final_text or "Done."
            else:
                badge = "Error"
                reply = f"Error: {result.get('error', 'Unknown')}"
                st.error(result.get("error", "Unknown"))

            # Voice output for operations briefing
            if agent_name == "operations" and final_text and status == "completed":
                safe_text = final_text[:600].replace("`", "").replace('"', '\\"').replace("\n", " ")
                tts_html = f"""<script>
                window.onload = function() {{
                  const u = new SpeechSynthesisUtterance("{safe_text}");
                  u.rate = 1.05; u.pitch = 1.0;
                  window.speechSynthesis.speak(u);
                }};
                </script>"""
                components.html(tts_html, height=0)

        # Save assistant reply to history
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": reply,
            "status_badge": badge,
        })
