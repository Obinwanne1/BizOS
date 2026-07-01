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
      * { box-sizing: border-box; margin: 0; padding: 0; }
      body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: transparent; }
      #mic {
        display: flex; align-items: center; justify-content: center; gap: 8px;
        background: #ffffff18; color: white; border: 1.5px solid #ffffff44;
        border-radius: 8px; padding: 9px 16px; font-size: 13px; font-weight: 600;
        cursor: pointer; width: 100%; transition: background 0.15s, border-color 0.15s;
        letter-spacing: 0.3px;
      }
      #mic:hover { background: #ffffff28; border-color: #ffffff88; }
      #mic.listening { background: #c0392b22; border-color: #c0392b; color: #ff9999; }
      #mic svg { flex-shrink: 0; }
      #status { font-size: 11px; color: rgba(255,255,255,0.5); margin-top: 7px; padding-left: 2px; }
      #transcript {
        font-size: 12px; font-weight: 500; color: rgba(255,255,255,0.9);
        margin-top: 6px; padding: 7px 10px; border-radius: 6px;
        background: rgba(255,255,255,0.1); min-height: 0; word-break: break-word;
        display: none; line-height: 1.5;
      }
    </style>
    <button id="mic" onclick="startListen()">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 1a4 4 0 0 1 4 4v7a4 4 0 0 1-8 0V5a4 4 0 0 1 4-4zm0 2a2 2 0 0 0-2 2v7a2 2 0 0 0 4 0V5a2 2 0 0 0-2-2zm6.364 7.636a1 1 0 0 1 1 1A7.364 7.364 0 0 1 13 18.9V21h2a1 1 0 0 1 0 2H9a1 1 0 0 1 0-2h2v-2.1A7.364 7.364 0 0 1 4.636 11.636a1 1 0 0 1 2 0 5.364 5.364 0 0 0 10.728 0 1 1 0 0 1 1-1z"/>
      </svg>
      Click to speak
    </button>
    <div id="status">Ready — Chrome / Edge only</div>
    <div id="transcript"></div>
    <script>
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    const btn = document.getElementById('mic');
    const status = document.getElementById('status');
    const transcript = document.getElementById('transcript');
    if (!SpeechRec) {
      status.textContent = 'Not supported in this browser.';
      btn.disabled = true; btn.style.opacity = '0.4';
    }
    function startListen() {
      const rec = new SpeechRec();
      rec.lang = 'en-US'; rec.continuous = false; rec.interimResults = true;
      btn.classList.add('listening');
      btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="6"/></svg> Listening...';
      status.textContent = 'Speak now...';
      rec.start();
      rec.onresult = (e) => {
        const t = Array.from(e.results).map(r => r[0].transcript).join('');
        transcript.textContent = t;
        transcript.style.display = 'block';
        if (e.results[e.results.length - 1].isFinal) {
          status.textContent = 'Done — copy transcript to chat above.';
        }
      };
      rec.onerror = (e) => { status.textContent = 'Error: ' + e.error; reset(); };
      rec.onend = reset;
    }
    function reset() {
      btn.classList.remove('listening');
      btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 1a4 4 0 0 1 4 4v7a4 4 0 0 1-8 0V5a4 4 0 0 1 4-4zm0 2a2 2 0 0 0-2 2v7a2 2 0 0 0 4 0V5a2 2 0 0 0-2-2zm6.364 7.636a1 1 0 0 1 1 1A7.364 7.364 0 0 1 13 18.9V21h2a1 1 0 0 1 0 2H9a1 1 0 0 1 0-2h2v-2.1A7.364 7.364 0 0 1 4.636 11.636a1 1 0 0 1 2 0 5.364 5.364 0 0 0 10.728 0 1 1 0 0 1 1-1z"/></svg> Click to speak';
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
                text = "".join(_buf)
                _box.markdown(
                    f"<div style='background:#f4f8f4;border:1px solid #c8dfc7;"
                    f"border-left:4px solid #407E3C;border-radius:8px;padding:14px 16px;"
                    f"font-size:13px;line-height:1.7;font-family:\"Segoe UI\",sans-serif;"
                    f"color:#1a2e1a;max-height:320px;overflow-y:auto;white-space:pre-wrap;'>"
                    f"<div style='font-size:10px;font-weight:700;letter-spacing:1px;"
                    f"color:#407E3C;margin-bottom:8px;text-transform:uppercase'>"
                    f"{agent_name.replace('_',' ').upper()} — generating</div>"
                    f"{text}<span style='display:inline-block;width:2px;height:14px;"
                    f"background:#407E3C;margin-left:2px;vertical-align:middle;"
                    f"animation:none'></span></div>",
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
                    f"<div style='background:#f4f8f4;border:1px solid #c8dfc7;"
                    f"border-left:4px solid #407E3C;border-radius:8px;padding:14px 16px;"
                    f"font-size:13px;line-height:1.7;font-family:\"Segoe UI\",sans-serif;"
                    f"color:#1a2e1a;max-height:320px;overflow-y:auto;white-space:pre-wrap;'>"
                    f"<div style='font-size:10px;font-weight:700;letter-spacing:1px;"
                    f"color:#5a9e56;margin-bottom:8px;text-transform:uppercase'>"
                    f"{agent_name.replace('_',' ').upper()} — complete</div>"
                    f"{final_text}</div>",
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
