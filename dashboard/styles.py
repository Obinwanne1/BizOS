import streamlit as st


BRAND_CSS = """
<style>
/* ── Sidebar ─────────────────────────────────────────────── */
[data-testid="stSidebar"] { background: #407E3C !important; }
[data-testid="stSidebar"] * { color: #ffffff !important; }
[data-testid="stSidebar"] a { color: #ffffff !important; }

/* ── Headings ────────────────────────────────────────────── */
h1, h2, h3 { color: #407E3C !important; }

/* ── Buttons ─────────────────────────────────────────────── */
.stButton > button {
    background: #407E3C !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
}
.stButton > button:hover { background: #5a9e56 !important; }

/* ── Legacy alert badge ──────────────────────────────────── */
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

/* ── Approval notification (pulsing) ─────────────────────── */
@keyframes pulse-red {
    0%   { box-shadow: 0 0 0 0 rgba(192,57,43,.6); }
    70%  { box-shadow: 0 0 0 8px rgba(192,57,43,0); }
    100% { box-shadow: 0 0 0 0 rgba(192,57,43,0); }
}
.notification-pulse {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #c0392b;
    color: white !important;
    font-size: 12px;
    font-weight: 700;
    padding: 5px 12px;
    border-radius: 20px;
    letter-spacing: 0.4px;
    animation: pulse-red 1.8s infinite;
    width: 100%;
    justify-content: center;
    text-decoration: none;
}
.notification-clear {
    display: inline-block;
    color: rgba(255,255,255,0.65) !important;
    font-size: 12px;
    padding: 4px 0;
}

/* ── Sidebar nav links ───────────────────────────────────── */
.nav-section {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.2px;
    color: rgba(255,255,255,0.5) !important;
    text-transform: uppercase;
    margin: 12px 0 4px 0;
}
.nav-link {
    display: block;
    color: rgba(255,255,255,0.9) !important;
    text-decoration: none !important;
    font-size: 13px;
    padding: 5px 8px;
    border-radius: 6px;
    transition: background 0.15s;
    margin-bottom: 2px;
}
.nav-link:hover { background: rgba(255,255,255,0.15) !important; }

/* ── Empty state card ────────────────────────────────────── */
.empty-state {
    text-align: center;
    padding: 48px 24px;
    border: 1.5px dashed #c8d9c7;
    border-radius: 12px;
    background: #f9fdf9;
    color: #6b8f6a;
}
.empty-state .empty-icon { font-size: 40px; margin-bottom: 12px; }
.empty-state .empty-title { font-size: 16px; font-weight: 700; margin-bottom: 6px; color: #407E3C; }
.empty-state .empty-sub   { font-size: 13px; color: #888; }

/* ── Exec error ──────────────────────────────────────────── */
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
