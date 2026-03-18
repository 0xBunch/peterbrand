"""BATCAVE - Entry Point with Navigation"""
import streamlit as st

# Page config - must be first
st.set_page_config(
    page_title="BATCAVE",
    page_icon="🦇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# BATCAVE branding - MUST be before st.navigation() to appear at top
with st.sidebar:
    st.markdown("""
    <div style="background: #161b22; border: 1px solid #30363d; border-left: 3px solid #c9a227; padding: 12px 16px; margin-bottom: 16px; text-align: center;">
        <div style="font-size: 1.4rem; font-weight: 700; color: #d4a746; letter-spacing: 0.2em;">BATCAVE</div>
    </div>
    """, unsafe_allow_html=True)

# Define navigation with explicit page order and titles
pages = [
    st.Page("pages/00_Draft_Board.py", title="Draft Board", icon="🦇", default=True),
    st.Page("pages/01_Position_Tiers.py", title="Position Tiers", icon="📊"),
    st.Page("pages/02_Budget_Strategy.py", title="Budget Strategy", icon="💰"),
    st.Page("pages/03_Draft_Tracker.py", title="Draft Tracker", icon="🎯"),
    st.Page("pages/04_Model_Tuning.py", title="Model Tuning", icon="⚙️"),
]

pg = st.navigation(pages)
pg.run()
