"""BATCAVE - Model Tuning Page"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data.database import get_connection
from model.ab_score import ABScoreCalculator, calculate_auction_value, calculate_bid_range
from app.config import DEFAULT_WEIGHTS
from app.theme import inject_theme

# Inject unified theme (page config handled by main.py navigation)
inject_theme()


def recalculate_all_scores(weights: dict):
    """Recalculate AB Scores for all players with new weights."""
    conn = get_connection()
    cursor = conn.cursor()

    calc = ABScoreCalculator(weights)

    # Get all players with projections
    cursor.execute("""
        SELECT
            p.id, p.name, p.mlb_team, p.positions, p.primary_position,
            proj.fpts, proj.gs,
            stats25.fpts as fpts_2025
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        LEFT JOIN projections stats25 ON p.id = stats25.player_id
            AND stats25.season = 2025 AND stats25.stat_type = 'actual'
        WHERE proj.fpts IS NOT NULL
    """)

    players = cursor.fetchall()
    count = 0

    for player in players:
        player_id = player[0]
        team = player[2] or 'FA'
        positions_str = player[3] or ''
        primary_pos = player[4] or 'DH'
        fpts_proj = player[5] or 0
        gs = player[6]
        fpts_2025 = player[7]

        positions = [p.strip() for p in positions_str.split(',') if p.strip()]
        is_pitcher = primary_pos in ['SP', 'RP']

        result = calc.calculate_ab_score(
            positions=positions,
            fpts_proj=fpts_proj,
            team=team,
            games_2025=gs if is_pitcher else None,
            fpts_2025=fpts_2025,
            is_pitcher=is_pitcher,
        )

        ab_score = result['ab_score']
        auction_value = calculate_auction_value(ab_score, primary_pos)
        floor, target, ceiling = calculate_bid_range(auction_value)

        # Update scores
        cursor.execute("""
            INSERT OR REPLACE INTO ab_scores
            (player_id, scarcity, slot, fpts_score, durability,
             team_quality, multi_pos, value_gap, health, contract,
             ab_score, auction_value)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            player_id,
            result['components']['scarcity'],
            result['components']['slot'],
            result['components']['fpts'],
            result['components']['durability'],
            result['components']['team_quality'],
            result['components']['multi_pos'],
            result['components']['value_gap'],
            result['components']['health'],
            result['components']['contract'],
            ab_score,
            auction_value
        ))

        # Update bid ranges in position_tiers
        cursor.execute("""
            UPDATE position_tiers
            SET bid_floor = ?, bid_target = ?, bid_ceiling = ?
            WHERE player_id = ?
        """, (floor, target, ceiling, player_id))

        count += 1

    conn.commit()
    conn.close()
    return count


def get_top_players_preview(weights: dict, limit: int = 10):
    """Get preview of top players with new weights."""
    conn = get_connection()
    cursor = conn.cursor()

    calc = ABScoreCalculator(weights)

    cursor.execute("""
        SELECT
            p.id, p.name, p.mlb_team, p.positions, p.primary_position,
            proj.fpts
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        WHERE proj.fpts IS NOT NULL
        ORDER BY proj.fpts DESC
        LIMIT ?
    """, (limit * 3,))  # Get more to filter

    players = cursor.fetchall()
    conn.close()

    results = []
    for player in players:
        team = player[2] or 'FA'
        positions_str = player[3] or ''
        primary_pos = player[4] or 'DH'
        fpts = player[5] or 0

        positions = [p.strip() for p in positions_str.split(',') if p.strip()]
        is_pitcher = primary_pos in ['SP', 'RP']

        result = calc.calculate_ab_score(
            positions=positions,
            fpts_proj=fpts,
            team=team,
            is_pitcher=is_pitcher,
        )

        results.append({
            'name': player[1],
            'team': team,
            'positions': positions_str,
            'fpts': fpts,
            'ab_score': result['ab_score'],
            'auction_value': calculate_auction_value(result['ab_score'], primary_pos),
            'components': result['components']
        })

    # Sort by AB Score
    results.sort(key=lambda x: x['ab_score'], reverse=True)
    return results[:limit]


def main():
    st.title("⚙️ Model Tuning")
    st.markdown("Adjust AB Score weights to prioritize different player attributes.")

    # Initialize session state for weights
    if 'weights' not in st.session_state:
        st.session_state.weights = DEFAULT_WEIGHTS.copy()

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Weight Sliders")
        st.caption("Adjust weights (will auto-normalize to 100%)")

        # Core components
        st.markdown("**Core Components**")

        new_weights = {}

        new_weights['scarcity'] = st.slider(
            "Positional Scarcity",
            min_value=0, max_value=50, value=int(st.session_state.weights['scarcity'] * 100),
            help="Premium for scarce positions (3B, OF, SP)"
        ) / 100

        new_weights['slot'] = st.slider(
            "Lineup Slot",
            min_value=0, max_value=50, value=int(st.session_state.weights['slot'] * 100),
            help="Value batting order position and team quality"
        ) / 100

        new_weights['fpts'] = st.slider(
            "FPTS Projection",
            min_value=0, max_value=50, value=int(st.session_state.weights['fpts'] * 100),
            help="Raw fantasy point output"
        ) / 100

        new_weights['durability'] = st.slider(
            "Durability",
            min_value=0, max_value=50, value=int(st.session_state.weights['durability'] * 100),
            help="2-year health track record"
        ) / 100

        new_weights['team_quality'] = st.slider(
            "Team Quality",
            min_value=0, max_value=50, value=int(st.session_state.weights['team_quality'] * 100),
            help="Contender vs rebuilder context"
        ) / 100

        new_weights['multi_pos'] = st.slider(
            "Multi-Position",
            min_value=0, max_value=50, value=int(st.session_state.weights['multi_pos'] * 100),
            help="Roster flexibility"
        ) / 100

        new_weights['value_gap'] = st.slider(
            "Value Gap",
            min_value=0, max_value=50, value=int(st.session_state.weights['value_gap'] * 100),
            help="Market misprice detection"
        ) / 100

        st.markdown("**New Components (R1)**")

        new_weights['health'] = st.slider(
            "Health Status",
            min_value=0, max_value=50, value=int(st.session_state.weights.get('health', 0) * 100),
            help="Current season injury status"
        ) / 100

        new_weights['contract'] = st.slider(
            "Contract Year",
            min_value=0, max_value=50, value=int(st.session_state.weights.get('contract', 0) * 100),
            help="Contract year motivation"
        ) / 100

        # Normalize
        total = sum(new_weights.values())
        if total > 0:
            new_weights = {k: v / total for k, v in new_weights.items()}

        st.divider()

        # Presets
        st.subheader("Presets")

        preset_col1, preset_col2 = st.columns(2)

        with preset_col1:
            if st.button("Balanced", use_container_width=True):
                st.session_state.weights = DEFAULT_WEIGHTS.copy()
                st.rerun()

            if st.button("Upside Chaser", use_container_width=True):
                st.session_state.weights = {
                    'scarcity': 0.20, 'slot': 0.15, 'fpts': 0.30,
                    'durability': 0.05, 'team_quality': 0.10,
                    'multi_pos': 0.05, 'value_gap': 0.10,
                    'health': 0.03, 'contract': 0.02
                }
                st.rerun()

        with preset_col2:
            if st.button("Stability First", use_container_width=True):
                st.session_state.weights = {
                    'scarcity': 0.20, 'slot': 0.20, 'fpts': 0.15,
                    'durability': 0.25, 'team_quality': 0.10,
                    'multi_pos': 0.05, 'value_gap': 0.02,
                    'health': 0.02, 'contract': 0.01
                }
                st.rerun()

            if st.button("Stars & Scrubs", use_container_width=True):
                st.session_state.weights = {
                    'scarcity': 0.30, 'slot': 0.10, 'fpts': 0.35,
                    'durability': 0.05, 'team_quality': 0.05,
                    'multi_pos': 0.05, 'value_gap': 0.05,
                    'health': 0.03, 'contract': 0.02
                }
                st.rerun()

        st.divider()

        # Apply button
        if st.button("🔄 Apply & Recalculate", type="primary", use_container_width=True):
            with st.spinner("Recalculating all player scores..."):
                st.session_state.weights = new_weights
                count = recalculate_all_scores(new_weights)
                st.success(f"Recalculated {count} player scores!")
                st.rerun()

    with col2:
        st.subheader("Live Preview")
        st.caption("Top players with current weight settings")

        # Show current weights
        st.markdown("**Current Weights:**")
        weight_display = " | ".join([
            f"{k}: {v*100:.0f}%"
            for k, v in sorted(new_weights.items(), key=lambda x: -x[1])
            if v > 0
        ])
        st.code(weight_display)

        st.divider()

        # Preview top players
        preview = get_top_players_preview(new_weights, limit=15)

        for i, player in enumerate(preview, 1):
            st.markdown(f"""
            <div style="
                background: #1a1a2e;
                padding: 12px;
                border-radius: 8px;
                margin: 8px 0;
            ">
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <strong>#{i} {player['name']}</strong>
                        <span style="color: #888; margin-left: 8px;">{player['team']} | {player['positions']}</span>
                    </div>
                    <div>
                        <span style="color: #4CAF50; font-weight: bold;">AB: {player['ab_score']:.1f}</span>
                        <span style="margin-left: 12px;">💰 ${player['auction_value']}</span>
                    </div>
                </div>
                <div style="margin-top: 8px; font-size: 0.85em; color: #888;">
                    FPTS: {player['fpts']:.0f} |
                    Scarcity: {player['components']['scarcity']:.0f} |
                    Slot: {player['components']['slot']:.0f} |
                    Durability: {player['components']['durability']:.0f} |
                    Team: {player['components']['team_quality']:.0f}
                </div>
            </div>
            """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
