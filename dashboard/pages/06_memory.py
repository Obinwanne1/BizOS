import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
load_dotenv()

import json
import streamlit as st
import pandas as pd
from orchestrator.state import get_all_memories, get_memories, save_memory, delete_memory
from dashboard.styles import apply_styles

st.set_page_config(page_title="Memory — BizOS", layout="wide")
apply_styles()

st.title("Agent Memory")
st.caption("What agents remember across runs. Edit or delete to correct bad memories.")

AGENTS = ["lead_gen", "content", "sales", "marketing", "product", "operations"]
MEMORY_TYPES = ["fact", "outcome", "preference", "lead_context", "campaign", "roadmap"]

tab_view, tab_add = st.tabs(["View & Manage", "Add Memory"])

with tab_view:
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        agent_filter = st.selectbox("Filter by agent", ["All"] + AGENTS)
    with col_filter2:
        type_filter = st.selectbox("Filter by type", ["All"] + MEMORY_TYPES)

    if agent_filter == "All":
        memories = get_all_memories(limit=200)
        if type_filter != "All":
            memories = [m for m in memories if m["memory_type"] == type_filter]
    else:
        memories = get_memories(
            agent_filter,
            memory_type=type_filter if type_filter != "All" else None,
            limit=100,
        )

    if not memories:
        st.info("No memories stored yet. Agents will write memories as they run.")
    else:
        st.caption(f"{len(memories)} memor{'y' if len(memories) == 1 else 'ies'} found.")

        for m in memories:
            with st.expander(
                f"[{m['agent'].replace('_',' ').upper()}] {m['memory_type']} — {m['key']}",
                expanded=False,
            ):
                col_val, col_meta, col_del = st.columns([4, 2, 1])
                with col_val:
                    new_val = st.text_area(
                        "Value", value=m["value"],
                        key=f"val_{m['id']}", height=80,
                    )
                    if st.button("Save", key=f"save_{m['id']}"):
                        save_memory(
                            m["agent"], m["memory_type"], m["key"],
                            new_val, confidence=m["confidence"], source="manual",
                        )
                        st.success("Updated.")
                        st.rerun()
                with col_meta:
                    st.caption(f"Confidence: {m['confidence']:.0%}")
                    st.caption(f"Source: {m['source']}")
                    st.caption(f"Updated: {m['updated_at'][:16]}")
                with col_del:
                    st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
                    if st.button("Delete", key=f"del_{m['id']}"):
                        delete_memory(m["id"])
                        st.warning("Deleted.")
                        st.rerun()

with tab_add:
    st.subheader("Add Manual Memory")
    st.caption("Inject knowledge an agent should carry into future runs.")

    c1, c2 = st.columns(2)
    with c1:
        new_agent = st.selectbox("Agent", AGENTS, key="new_agent")
        new_type = st.selectbox("Type", MEMORY_TYPES, key="new_type")
    with c2:
        new_key = st.text_input("Key", placeholder="e.g. best_linkedin_hook", key="new_key")
        new_conf = st.slider("Confidence", 0.0, 1.0, 1.0, 0.1, key="new_conf")

    new_value = st.text_area("Value", placeholder="What should the agent remember?", key="new_value", height=100)

    if st.button("Save Memory", type="primary"):
        if new_key.strip() and new_value.strip():
            save_memory(new_agent, new_type, new_key.strip(), new_value.strip(),
                        confidence=new_conf, source="manual")
            st.success(f"Memory saved for {new_agent}.")
            st.rerun()
        else:
            st.warning("Key and value are required.")
