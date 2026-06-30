import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from orchestrator.router import dispatch
from dashboard.styles import apply_styles

st.set_page_config(page_title="Content — BizOS", layout="wide")
apply_styles()

st.title("Content Engine")
st.caption("Generate authoritative RE industry content. Agent researches current news before writing.")

st.subheader("Generate")

col1, col2, col3 = st.columns(3)
with col1:
    platform = st.selectbox("Platform", ["LinkedIn", "Twitter", "Instagram"])
with col2:
    content_type = st.selectbox(
        "Type", ["Market Update", "Agent Tip", "Product Insight", "Industry News", "Case Study"]
    )
with col3:
    topic = st.text_input("Topic (optional)", placeholder="e.g. Rising mortgage rates impact on agents")

if st.button("Generate Content"):
    with st.spinner("Content agent researching and writing..."):
        result = dispatch("content", "manual_trigger", {
            "platform": platform,
            "content_type": content_type,
            "topic": topic,
        })

    if result.get("status") == "awaiting_approval":
        st.success("Draft ready — review it in Approvals before it goes live.")
        preview = result.get("preview", {})
        if preview.get("body"):
            st.markdown("---")
            st.markdown(f"**{preview.get('title', 'Draft')}**")
            if preview.get("hook"):
                st.markdown(f"_{preview['hook']}_")
            st.text_area("Full draft", preview["body"], height=220, disabled=True, key="content_preview")
            if preview.get("hashtags"):
                st.caption("Tags: " + " ".join(preview["hashtags"]))
    elif result.get("status") == "failed":
        st.error(result.get("error", "Agent failed"))
    else:
        st.info(result.get("status", "Done"))

st.markdown("---")
st.subheader("Content Angles for RE SaaS")

col_a, col_b, col_c = st.columns(3)
with col_a:
    st.markdown("**LinkedIn**")
    st.markdown("""
- Fed rate decision impact on listings
- 5 signs a buyer is serious vs browsing
- How top agents use AI to close faster
- Why your CRM is costing you listings
- What separates $1M producers from the rest
""")
with col_b:
    st.markdown("**Twitter / X**")
    st.markdown("""
- Market data threads (weekly)
- 3-tweet agent tip formats
- Industry news commentary
- Hot takes on proptech trends
- Live market update threads
""")
with col_c:
    st.markdown("**Instagram**")
    st.markdown("""
- Before/after workflow comparisons
- Client success story visuals
- Property tech behind-the-scenes
- Day in the life of a power agent
- Market stat infographics
""")

st.markdown("---")
st.caption("Schedule: Content agent runs Mon / Wed / Fri at 08:00 automatically.")
