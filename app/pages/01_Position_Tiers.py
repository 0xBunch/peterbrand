"""Position Tiers - Browse players by position and tier."""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data.database import get_connection
from app.config import BUDGET_STRATEGY, POSITIONAL_SCARCITY

st.set_page_config(page_title="Position Tiers", page_icon="📋", layout="wide")


def get_players_by_position(position: str, tier: int = None, limit: int = 50):
    """Get players for a position, optionally filtered by tier."""
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            p.id, p.name, p.mlb_team, p.positions,
            proj.fpts, proj.hr, proj.rbi, proj.sb, proj.avg,
            proj.w, proj.sv, proj.k_pitch, proj.era, proj.ip,
            COALESCE(ab.ab_score, 50) as ab_score,
            COALESCE(ab.auction_value, 1) as auction_value,
            COALESCE(pt.tier, 4) as tier,
            COALESCE(pt.bid_floor, 1) as bid_floor,
            COALESCE(pt.bid_target, 1) as bid_target,
            COALESCE(pt.bid_ceiling, 1) as bid_ceiling,
            dp.id as drafted
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        LEFT JOIN ab_scores ab ON p.id = ab.player_id
        LEFT JOIN position_tiers pt ON p.id = pt.player_id AND pt.position = ?
        LEFT JOIN draft_picks dp ON p.id = dp.player_id
        WHERE p.positions LIKE ? AND proj.fpts IS NOT NULL
    """

    params = [position, f'%{position}%']

    if tier:
        query += " AND pt.tier = ?"
        params.append(tier)

    query += " ORDER BY proj.fpts DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return rows


def render_player_card(player, position: str, is_pitcher: bool = False):
    """Render a player card with stats and bidding info."""
    name = player[1]
    team = player[2] or 'FA'
    positions = player[3] or position
    fpts = player[4] or 0
    tier = player[16]
    bid_floor = player[17]
    bid_target = player[18]
    bid_ceiling = player[19]
    ab_score = player[14]
    is_drafted = player[20] is not None

    # Tier colors
    tier_colors = {1: '#ffd700', 2: '#c0c0c0', 3: '#cd7f32', 4: '#555'}
    tier_names = {1: 'Elite', 2: 'Solid', 3: 'Value', 4: 'Depth'}

    if is_drafted:
        bg_color = '#3d3d3d'
        opacity = '0.6'
    else:
        bg_color = '#1a1a2e'
        opacity = '1'

    # Build stats string
    if is_pitcher:
        era = player[12] or 0
        ip = player[13] or 0
        w = player[9] or 0
        sv = player[10] or 0
        k = player[11] or 0
        stats_str = f"W:{w} | SV:{sv} | K:{k} | ERA:{era:.2f} | IP:{ip:.0f}"
    else:
        hr = player[5] or 0
        rbi = player[6] or 0
        sb = player[7] or 0
        avg = player[8] or 0
        stats_str = f"HR:{hr} | RBI:{rbi} | SB:{sb} | AVG:{avg:.3f}"

    st.markdown(f"""
    <div style="
        background: {bg_color};
        border-radius: 8px;
        padding: 12px;
        margin: 6px 0;
        border-left: 4px solid {tier_colors.get(tier, '#555')};
        opacity: {opacity};
    ">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong style="font-size: 1.1em;">{name}</strong>
                <span style="color: #888; margin-left: 8px;">{team} | {positions}</span>
                {'<span style="background: #4CAF50; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.7em; margin-left: 8px;">DRAFTED</span>' if is_drafted else ''}
            </div>
            <div style="text-align: right;">
                <span style="background: {tier_colors.get(tier, '#555')}; color: black; padding: 2px 8px; border-radius: 4px; font-size: 0.8em;">
                    T{tier} {tier_names.get(tier, '')}
                </span>
            </div>
        </div>
        <div style="margin-top: 8px; display: flex; justify-content: space-between;">
            <div>
                <span style="color: #4CAF50; font-weight: bold;">{fpts:.0f} FPTS</span>
                <span style="color: #888; margin-left: 12px;">{stats_str}</span>
            </div>
            <div>
                <span style="color: #888;">AB: {ab_score:.0f}</span>
                <span style="margin-left: 12px;">
                    💰 <span style="color: #f39c12;">${bid_floor}</span> /
                    <strong style="color: #27ae60;">${bid_target}</strong> /
                    <span style="color: #e74c3c;">${bid_ceiling}</span>
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def main():
    st.title("📋 Position Tiers")
    st.markdown("Browse players by position. Tier 1 = Elite, Tier 4 = Replacement level.")

    # Position selector
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        position = st.selectbox(
            "Select Position",
            ['OF', 'SP', '3B', '1B', '2B', 'SS', 'C', 'DH', 'RP'],
            format_func=lambda x: f"{x} - {BUDGET_STRATEGY.get(x, {}).get('strategy', '')[:40]}..."
        )

    with col2:
        tier_filter = st.selectbox(
            "Filter by Tier",
            [None, 1, 2, 3, 4],
            format_func=lambda x: "All Tiers" if x is None else f"Tier {x}"
        )

    with col3:
        show_drafted = st.checkbox("Show Drafted", value=False)

    # Position context
    pos_info = BUDGET_STRATEGY.get(position, {})
    scarcity = POSITIONAL_SCARCITY.get(position, {})

    st.markdown(f"""
    **Budget Target:** ${pos_info.get('target', 0)} (${pos_info.get('min', 0)}-${pos_info.get('max', 0)})
    | **Slots Needed:** {pos_info.get('needed', 0)}
    | **Scarcity Score:** {scarcity.get('score', 50)}
    | **Strategy:** {pos_info.get('strategy', '')}
    """)

    st.divider()

    # Get players
    is_pitcher = position in ['SP', 'RP']
    players = get_players_by_position(position, tier_filter, limit=100)

    if not show_drafted:
        players = [p for p in players if p[20] is None]

    if not players:
        st.warning("No players found for this position/tier combination.")
        return

    # Group by tier
    tiers = {1: [], 2: [], 3: [], 4: []}
    for p in players:
        tier = p[16] or 4
        tiers[tier].append(p)

    # Display
    if tier_filter:
        # Single tier view
        st.subheader(f"Tier {tier_filter} - {len(tiers.get(tier_filter, []))} players")
        for player in tiers.get(tier_filter, []):
            render_player_card(player, position, is_pitcher)
    else:
        # All tiers view
        tier_tabs = st.tabs(["Tier 1 (Elite)", "Tier 2 (Solid)", "Tier 3 (Value)", "Tier 4 (Depth)"])

        for i, tab in enumerate(tier_tabs):
            tier_num = i + 1
            with tab:
                tier_players = tiers.get(tier_num, [])
                st.caption(f"{len(tier_players)} players")
                for player in tier_players[:30]:  # Limit display
                    render_player_card(player, position, is_pitcher)


if __name__ == "__main__":
    main()
