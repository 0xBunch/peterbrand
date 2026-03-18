"""BATCAVE - Draft Tracker Page"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data.database import get_connection, record_draft_pick, get_team_status, init_league_teams
from app.config import OPPONENTS, AVAILABLE_BUDGET, KEEPERS
from app.theme import inject_theme, render_sidebar_brand

st.set_page_config(page_title="BATCAVE - Tracker", page_icon="🎯", layout="wide")

# Inject unified theme
inject_theme()


def search_players(query: str, limit: int = 10):
    """Search for undrafted players."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.id, p.name, p.mlb_team, p.positions,
            proj.fpts,
            COALESCE(ab.auction_value, 1) as auction_value,
            COALESCE(pt.bid_floor, 1) as bid_floor,
            COALESCE(pt.bid_target, 1) as bid_target,
            COALESCE(pt.bid_ceiling, 1) as bid_ceiling
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        LEFT JOIN ab_scores ab ON p.id = ab.player_id
        LEFT JOIN position_tiers pt ON p.id = pt.player_id
            AND pt.position = p.primary_position
        LEFT JOIN draft_picks dp ON p.id = dp.player_id
        WHERE dp.id IS NULL
            AND p.name LIKE ?
            AND proj.fpts IS NOT NULL
        ORDER BY proj.fpts DESC
        LIMIT ?
    """, (f'%{query}%', limit))

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_recent_picks(limit: int = 20):
    """Get recent draft picks."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            dp.pick_order, p.name, p.positions, dp.team, dp.salary,
            COALESCE(ab.auction_value, 1) as expected_value,
            dp.is_keeper
        FROM draft_picks dp
        JOIN players p ON dp.player_id = p.id
        LEFT JOIN ab_scores ab ON p.id = ab.player_id
        ORDER BY dp.pick_order DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_best_available(position: str = None, limit: int = 10):
    """Get best available players."""
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            p.id, p.name, p.mlb_team, p.positions,
            proj.fpts,
            COALESCE(ab.ab_score, 50) as ab_score,
            COALESCE(ab.auction_value, 1) as auction_value,
            COALESCE(pt.tier, 4) as tier,
            COALESCE(pt.bid_target, 1) as bid_target
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        LEFT JOIN ab_scores ab ON p.id = ab.player_id
        LEFT JOIN position_tiers pt ON p.id = pt.player_id
            AND pt.position = p.primary_position
        LEFT JOIN draft_picks dp ON p.id = dp.player_id
        WHERE dp.id IS NULL AND proj.fpts IS NOT NULL
    """

    params = []
    if position:
        query += " AND p.positions LIKE ?"
        params.append(f'%{position}%')

    query += " ORDER BY proj.fpts DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


def main():
    # Sidebar branding
    with st.sidebar:
        render_sidebar_brand()
        st.markdown("---")
        st.caption("Record picks and track value in real-time")

    st.title("🎯 Live Draft Tracker")
    st.markdown("Record picks in real-time and track value.")

    # Initialize teams if needed
    if 'teams_initialized' not in st.session_state:
        init_league_teams(OPPONENTS)
        # Add your team
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO league_teams (name, budget_remaining, tendency, notes)
            VALUES ('Austin Bats', ?, 'Your Team', 'Stars & scrubs, punt pitching')
        """, (AVAILABLE_BUDGET,))
        conn.commit()
        conn.close()
        st.session_state.teams_initialized = True

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📝 Record Pick", "📊 Draft Board", "🏆 Best Available"])

    with tab1:
        st.subheader("Record a Draft Pick")

        col1, col2 = st.columns([2, 1])

        with col1:
            search_query = st.text_input("Search Player", placeholder="Start typing player name...")

            if search_query and len(search_query) >= 2:
                results = search_players(search_query)

                if results:
                    player_options = {
                        f"{r[1]} ({r[3]}) - {r[2]} | {r[4]:.0f} FPTS | Target: ${r[7]}": r
                        for r in results
                    }

                    selected = st.selectbox("Select Player", list(player_options.keys()))
                    player = player_options.get(selected)

                    if player:
                        st.info(f"""
                        **{player[1]}** ({player[3]}) - {player[2]}
                        - Projected FPTS: {player[4]:.0f}
                        - Bid Range: ${player[6]} / **${player[7]}** / ${player[8]}
                        """)
                else:
                    st.warning("No players found matching that name.")

        with col2:
            teams = ['Austin Bats'] + list(OPPONENTS.keys())
            team = st.selectbox("Drafting Team", teams)

            salary = st.number_input("Salary", min_value=1, max_value=100, value=1)

            is_keeper = st.checkbox("Keeper Pick")

            if st.button("Record Pick", type="primary", use_container_width=True):
                if 'player' in dir() and player:
                    record_draft_pick(player[0], team, salary, is_keeper)
                    st.success(f"Recorded: {player[1]} to {team} for ${salary}")
                    st.rerun()
                else:
                    st.error("Please select a player first.")

        st.divider()

        # Recent picks
        st.subheader("Recent Picks")
        recent = get_recent_picks(15)

        if recent:
            for pick in recent:
                pick_num, name, positions, team, sal, expected, is_keeper = pick

                # Value indicator
                if expected > 0:
                    diff = sal - expected
                    if diff < -5:
                        value_badge = f"🔥 STEAL (-${abs(diff):.0f})"
                        badge_color = "#27ae60"
                    elif diff > 5:
                        value_badge = f"📈 OVERPAY (+${diff:.0f})"
                        badge_color = "#e74c3c"
                    else:
                        value_badge = "✓ Fair"
                        badge_color = "#3498db"
                else:
                    value_badge = ""
                    badge_color = "#888"

                keeper_badge = "🔒" if is_keeper else ""

                st.markdown(f"""
                <div style="
                    background: #1a1a2e;
                    padding: 8px 12px;
                    border-radius: 4px;
                    margin: 4px 0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <div>
                        <strong>#{pick_num}</strong>
                        <span style="margin-left: 12px;">{name}</span>
                        <span style="color: #888; margin-left: 8px;">({positions})</span>
                        {keeper_badge}
                    </div>
                    <div>
                        <span style="color: #888;">{team}</span>
                        <span style="margin-left: 12px; font-weight: bold;">${sal}</span>
                        <span style="color: {badge_color}; margin-left: 8px;">{value_badge}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No picks recorded yet.")

    with tab2:
        st.subheader("Team Budgets")

        teams = get_team_status()

        if teams:
            # Create columns for team cards
            cols = st.columns(3)

            for i, team in enumerate(teams):
                with cols[i % 3]:
                    name = team['name']
                    budget = team['budget_remaining'] or 320
                    players = team['players_drafted'] or 0
                    tendency = team['tendency'] or ''

                    # Highlight your team
                    is_you = name == 'Austin Bats'
                    border_color = '#4CAF50' if is_you else '#333'

                    st.markdown(f"""
                    <div style="
                        background: #1a1a2e;
                        padding: 12px;
                        border-radius: 8px;
                        margin: 8px 0;
                        border: 2px solid {border_color};
                    ">
                        <div style="font-weight: bold;">{name} {'(YOU)' if is_you else ''}</div>
                        <div style="font-size: 1.5em; color: #4CAF50;">${budget}</div>
                        <div style="color: #888;">{players} players</div>
                        <div style="color: #666; font-size: 0.8em; margin-top: 4px;">{tendency[:40]}</div>
                    </div>
                    """, unsafe_allow_html=True)

    with tab3:
        st.subheader("Best Available")

        pos_filter = st.selectbox(
            "Filter by Position",
            [None, 'OF', 'SP', '3B', '1B', '2B', 'SS', 'C', 'DH', 'RP'],
            format_func=lambda x: "All Positions" if x is None else x
        )

        best = get_best_available(pos_filter, limit=25)

        if best:
            for player in best:
                id, name, team, positions, fpts, ab_score, auction_val, tier, bid_target = player

                tier_colors = {1: '#ffd700', 2: '#c0c0c0', 3: '#cd7f32', 4: '#555'}

                st.markdown(f"""
                <div style="
                    background: #1a1a2e;
                    padding: 10px 12px;
                    border-radius: 4px;
                    margin: 4px 0;
                    border-left: 3px solid {tier_colors.get(tier, '#555')};
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <div>
                        <strong>{name}</strong>
                        <span style="color: #888; margin-left: 8px;">{team} | {positions}</span>
                        <span style="
                            background: {tier_colors.get(tier, '#555')};
                            color: black;
                            padding: 1px 6px;
                            border-radius: 4px;
                            font-size: 0.7em;
                            margin-left: 8px;
                        ">T{tier}</span>
                    </div>
                    <div>
                        <span style="color: #4CAF50; font-weight: bold;">{fpts:.0f}</span>
                        <span style="color: #888; margin-left: 8px;">FPTS</span>
                        <span style="margin-left: 16px;">💰 <strong>${bid_target}</strong></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("No players available.")


if __name__ == "__main__":
    main()
