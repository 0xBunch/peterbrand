"""Peter Brand - Fantasy Baseball Draft Planner"""
import streamlit as st
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import (
    LEAGUE_NAME, SALARY_CAP, KEEPER_TOTAL, AVAILABLE_BUDGET,
    BUDGET_STRATEGY, KEEPERS, OPPONENTS
)

st.set_page_config(
    page_title="Peter Brand",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .tier-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 8px;
        padding: 12px;
        margin: 6px 0;
        border-left: 4px solid;
    }
    .tier-1 { border-color: #ffd700; }
    .tier-2 { border-color: #c0c0c0; }
    .tier-3 { border-color: #cd7f32; }
    .tier-4 { border-color: #555; }

    .stat-highlight {
        font-size: 1.5em;
        font-weight: bold;
        color: #4CAF50;
    }

    .budget-warning {
        background: #ff6b6b;
        padding: 8px;
        border-radius: 4px;
        color: white;
    }

    .keeper-badge {
        background: #4CAF50;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8em;
    }

    div[data-testid="stMetricValue"] {
        font-size: 2rem;
    }
</style>
""", unsafe_allow_html=True)


def main():
    st.title("⚾ Peter Brand")
    st.markdown(f"### {LEAGUE_NAME} Draft Command Center")

    # Sidebar - Budget Overview
    with st.sidebar:
        st.header("💰 Budget Status")

        # Get current draft state from session
        if 'spent' not in st.session_state:
            st.session_state.spent = 0
        if 'players_drafted' not in st.session_state:
            st.session_state.players_drafted = 0

        remaining = AVAILABLE_BUDGET - st.session_state.spent

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Budget", f"${SALARY_CAP}")
            st.metric("Keepers", f"${KEEPER_TOTAL}")
        with col2:
            st.metric("Available", f"${AVAILABLE_BUDGET}")
            st.metric("Remaining", f"${remaining}")

        st.divider()

        # Keepers
        st.subheader("🔒 Your Keepers")
        for name, info in KEEPERS.items():
            st.write(f"**{name}** ({info['position']}) - ${info['salary']}")

        st.divider()

        # Quick links
        st.subheader("📊 Navigation")
        st.page_link("pages/01_Position_Tiers.py", label="Position Tiers", icon="📋")
        st.page_link("pages/02_Budget_Strategy.py", label="Budget Strategy", icon="💵")
        st.page_link("pages/03_Draft_Tracker.py", label="Live Draft", icon="🎯")
        st.page_link("pages/04_Model_Tuning.py", label="Model Settings", icon="⚙️")

    # Main content - Dashboard
    st.markdown("---")

    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Draft Budget",
            f"${remaining}",
            delta=f"-${st.session_state.spent}" if st.session_state.spent > 0 else None
        )

    with col2:
        # Calculate avg $ per player remaining
        slots_needed = sum(v['needed'] for v in BUDGET_STRATEGY.values() if v['needed'] > 0)
        slots_filled = st.session_state.players_drafted
        slots_remaining = max(1, slots_needed - slots_filled)
        avg_per_player = remaining // slots_remaining
        st.metric("Avg $/Player Left", f"${avg_per_player}", delta=f"{slots_remaining} slots")

    with col3:
        st.metric("Positions Locked", "2/9", delta="2B, SS filled")

    with col4:
        st.metric("Draft Target", f"${AVAILABLE_BUDGET - 45}", delta="Save $45 FAAB")

    st.markdown("---")

    # Position needs summary
    st.subheader("📋 Position Needs")

    pos_cols = st.columns(9)
    positions = ['C', '1B', '2B', '3B', 'SS', 'OF', 'DH', 'SP', 'RP']

    for i, pos in enumerate(positions):
        with pos_cols[i]:
            need = BUDGET_STRATEGY[pos]['needed']
            budget = BUDGET_STRATEGY[pos]['target']

            if need == 0:
                st.success(f"**{pos}**")
                st.write("✅ Filled")
            else:
                st.info(f"**{pos}**")
                st.write(f"Need: {need}")
                st.write(f"${budget}")

    st.markdown("---")

    # Opponent scouting quick view
    st.subheader("🔍 Opponent Tendencies")

    opp_cols = st.columns(3)
    opponents_list = list(OPPONENTS.items())

    for i, (name, info) in enumerate(opponents_list):
        with opp_cols[i % 3]:
            st.markdown(f"**{name}**")
            st.caption(f"_{info['style']}_")
            st.write(info['tendency'])

    st.markdown("---")

    # Quick start guide
    with st.expander("📖 How to Use Peter Brand"):
        st.markdown("""
        ### Draft Night Workflow

        1. **Position Tiers** - Browse players by position and tier. Each player shows:
           - Projected FPTS and key stats
           - AB Score (composite value rating)
           - Bid range: Floor / Target / Ceiling

        2. **Budget Strategy** - See your spending plan by position
           - Track budget deployment as you draft
           - Get alerts when overspending

        3. **Live Draft** - Track picks in real-time
           - Mark players as drafted
           - See best available by position
           - Value alerts for bargains/overpays

        4. **Model Tuning** - Adjust AB Score weights
           - Emphasize durability, upside, or scarcity
           - Recalculate all values in real-time

        ### The AB Score Formula

        Your player valuation combines:
        - **Positional Scarcity (25%)** - Premium for scarce positions
        - **Lineup Slot (20%)** - Batting order / rotation position
        - **FPTS Projection (18%)** - Raw fantasy points
        - **Durability (14%)** - 2-year health track record
        - **Team Quality (10%)** - Contender vs rebuilder
        - **Multi-Position (8%)** - Roster flexibility
        - **Value Gap (5%)** - Market misprice detection
        """)


if __name__ == "__main__":
    main()
