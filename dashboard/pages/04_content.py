import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
from orchestrator.router import dispatch

st.set_page_config(page_title="Content — BizOS", layout="wide")
st.markdown("""
<style>
[data-testid="stSidebar"] { background: #407E3C !important; }
[data-testid="stSidebar"] * { color: white !important; }
h1, h2, h3 { color: #407E3C !important; }
.stButton > button { background: #407E3C !important; color: white !important; border: none !important; border-radius: 6px !important; }
</style>""", unsafe_allow_html=True)

st.title("✍️ Content Engine")

st.subheader("Generate New Content")

col1, col2, col3 = st.columns(3)
with col1:
    platform = st.selectbox("Platform", ["LinkedIn", "Twitter", "Instagram"])
with col2:
    content_type = st.selectbox("Type", ["Market Update", "Agent Tip", "Product Insight", "Industry News", "Case Study"])
with col3:
    topic = st.text_input("Topic (optional)", placeholder="e.g. Rising mortgage rates")

if st.button("✍️ Generate Content"):
    with st.spinner("Content Agent is writing..."):
        result = dispatch("content", "manual_trigger", {
            "platform": platform,
            "content_type": content_type,
            "topic": topic,
        })

    if result.get("status") == "awaiting_approval":
        st.success("Content draft ready — go to Approvals to review and schedule.")
        preview = result.get("preview", {})
        if preview:
            st.markdown("---")
            st.markdown(f"**Preview: {preview.get('title', '')}**")
            st.markdown(f"*{preview.get('hook', '')}*")
            st.text_area("Draft", preview.get("body", ""), height=200, disabled=True)
    elif result.get("status") == "completed":
        st.success("Done.")
    else:
        st.error(result.get("error", "Unknown error"))

st.markdown("---")
st.subheader("Content Ideas")
st.markdown("""
**LinkedIn (high engagement for RE pros):**
- "What the Fed's rate decision means for your listings this quarter"
- "5 signs a buyer is serious vs. window shopping"
- "How top agents are using AI to close 30% faster"

**Twitter/X:**
- Real-time market data threads
- Quick tips in 3-tweet format
- Industry news commentary

**Instagram:**
- Behind-the-scenes of property tech
- Before/after workflow comparisons
- Client success stories (visual)
""")

st.caption("Schedule: Content Agent runs Mon/Wed/Fri at 8:00 AM automatically. Or trigger manually above.")
