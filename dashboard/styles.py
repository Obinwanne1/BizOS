import streamlit as st


BRAND_CSS = """
<style>
[data-testid="stSidebar"] { background: #407E3C !important; }
[data-testid="stSidebar"] * { color: #ffffff !important; }
[data-testid="stSidebar"] a { color: #ffffff !important; }
h1, h2, h3 { color: #407E3C !important; }
.stButton > button {
    background: #407E3C !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
}
.stButton > button:hover { background: #5a9e56 !important; }
.alert-badge {
    display: inline-block;
    background: #c0392b;
    color: white;
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 10px;
    letter-spacing: 0.5px;
}
.exec-error {
    background: #fff3cd;
    border-left: 4px solid #e67e22;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 13px;
    margin-top: 4px;
}
</style>
"""


def apply_styles():
    st.markdown(BRAND_CSS, unsafe_allow_html=True)
