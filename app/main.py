"""BATCAVE - Entry Point with Navigation"""
import streamlit as st

# Page config - must be first
st.set_page_config(
    page_title="BATCAVE",
    page_icon="🦇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS to inject BATCAVE branding at TOP of sidebar via ::before
st.markdown("""
<style>
[data-testid="stSidebar"] > div:first-child::before {
    content: "BATCAVE";
    display: block;
    background: #161b22;
    border: 1px solid #30363d;
    border-left: 3px solid #c9a227;
    padding: 12px 16px;
    margin: 0 0 16px 0;
    text-align: center;
    font-size: 1.4rem;
    font-weight: 700;
    color: #d4a746;
    letter-spacing: 0.2em;
    font-family: 'JetBrains Mono', monospace;
}
</style>
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
