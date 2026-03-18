"""BATCAVE - Entry Point with Navigation"""
import streamlit as st

# Page config - must be first
st.set_page_config(
    page_title="BATCAVE",
    page_icon="🦇",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
