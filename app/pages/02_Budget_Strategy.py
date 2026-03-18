"""BATCAVE - Budget Strategy Page"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.theme import inject_theme, COLORS
from app.config import (
    BUDGET_STRATEGY, AVAILABLE_BUDGET, FAAB_RESERVE_TARGET, KEEPERS
)

# Inject unified theme (page config handled by main.py navigation)
inject_theme()


def get_draft_status():
    """Get current draft spending by position."""
    try:
        from data.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                p.primary_position,
                COUNT(*) as players,
                SUM(dp.salary) as spent
            FROM draft_picks dp
            JOIN players p ON dp.player_id = p.id
            WHERE dp.team = 'Austin Bats'
            GROUP BY p.primary_position
        """)

        rows = cursor.fetchall()
        conn.close()

        return {row[0]: {'players': row[1], 'spent': row[2]} for row in rows}
    except Exception as e:
        st.warning(f"Could not load draft data: {e}")
        return {}


def render_position_budget(position: str, budget_info: dict, spent_info: dict):
    """Render budget card for a position."""
    needed = budget_info['needed']
    target = budget_info['target']
    min_budget = budget_info['min']
    max_budget = budget_info['max']
    strategy = budget_info['strategy']

    pos_spent = spent_info.get(position, {})
    spent = pos_spent.get('spent', 0) or 0
    players_drafted = pos_spent.get('players', 0) or 0

    remaining = target - spent
    slots_remaining = needed - players_drafted

    # Status color using theme colors
    if needed == 0:
        status_color = COLORS['positive']
        status_text = 'KEEPER'
    elif slots_remaining == 0:
        status_color = COLORS['positive']
        status_text = 'FILLED'
    elif spent > max_budget:
        status_color = COLORS['negative']
        status_text = 'OVER'
    elif spent > target:
        status_color = COLORS['warning']
        status_text = 'HIGH'
    else:
        status_color = COLORS['info']
        status_text = 'OK'

    # Progress percentage
    progress = min(100, (spent / target * 100)) if target > 0 else 0

    st.markdown(f"""
    <div style="
        background: {COLORS['panel']};
        border-radius: 4px;
        padding: 16px;
        margin: 8px 0;
        border-left: 4px solid {status_color};
    ">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <span style="font-size: 1.5em; font-weight: bold; color: {COLORS['text']};">{position}</span>
                <span style="
                    background: {status_color};
                    color: {COLORS['bg']};
                    padding: 2px 8px;
                    border-radius: 2px;
                    font-size: 0.7em;
                    margin-left: 8px;
                    font-weight: 600;
                ">{status_text}</span>
            </div>
            <div style="text-align: right;">
                <span style="font-size: 1.3em; color: {status_color};">${spent}</span>
                <span style="color: {COLORS['text_muted']};"> / ${target}</span>
            </div>
        </div>

        <div style="margin-top: 8px; background: {COLORS['border']}; border-radius: 2px; height: 6px;">
            <div style="
                background: {status_color};
                width: {progress}%;
                height: 100%;
                border-radius: 2px;
            "></div>
        </div>

        <div style="margin-top: 12px; display: flex; justify-content: space-between; color: {COLORS['text_muted']}; font-size: 0.8em;">
            <div>
                <strong>Need:</strong> {slots_remaining} player{'s' if slots_remaining != 1 else ''}
                <span style="margin-left: 16px;"><strong>Range:</strong> ${min_budget}-${max_budget}</span>
            </div>
            <div>
                <strong>Remaining:</strong> ${remaining}
            </div>
        </div>

        <div style="margin-top: 8px; color: {COLORS['text_dim']}; font-size: 0.85em;">
            💡 {strategy}
        </div>
    </div>
    """, unsafe_allow_html=True)


def main():
    st.title("💵 Budget Strategy")
    st.markdown("Position-by-position spending plan and deployment tracking.")

    # Get draft status with error handling
    spent_data = get_draft_status()
    total_spent = sum(d.get('spent', 0) or 0 for d in spent_data.values())
    total_players = sum(d.get('players', 0) or 0 for d in spent_data.values())

    remaining = AVAILABLE_BUDGET - total_spent
    target_spend = AVAILABLE_BUDGET - FAAB_RESERVE_TARGET

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Budget", f"${AVAILABLE_BUDGET}")

    with col2:
        st.metric("Spent", f"${total_spent}", delta=f"{total_players} players")

    with col3:
        st.metric("Remaining", f"${remaining}")

    with col4:
        faab_projected = remaining if total_spent >= target_spend else FAAB_RESERVE_TARGET
        st.metric("FAAB Projected", f"${faab_projected}", delta="Target: $45")

    st.divider()

    # Keepers
    st.subheader("🔒 Keepers (Pre-Draft)")
    keeper_cols = st.columns(3)
    for i, (name, info) in enumerate(KEEPERS.items()):
        with keeper_cols[i]:
            st.info(f"**{name}** ({info['position']}) - ${info['salary']}")

    st.divider()

    # Budget by position
    st.subheader("📊 Budget by Position")

    # Hitting positions
    st.markdown("### Hitting")
    hit_positions = ['C', '1B', '2B', '3B', 'SS', 'OF', 'DH']
    hit_cols = st.columns(2)

    for i, pos in enumerate(hit_positions):
        with hit_cols[i % 2]:
            render_position_budget(pos, BUDGET_STRATEGY[pos], spent_data)

    st.markdown("### Pitching")
    pitch_positions = ['SP', 'RP']
    pitch_cols = st.columns(2)

    for i, pos in enumerate(pitch_positions):
        with pitch_cols[i]:
            render_position_budget(pos, BUDGET_STRATEGY[pos], spent_data)

    st.divider()

    # Budget allocation table
    st.subheader("📋 Budget Allocation Summary")

    budget_data = []
    for pos, info in BUDGET_STRATEGY.items():
        spent_info = spent_data.get(pos, {})
        budget_data.append({
            'Position': pos,
            'Slots Needed': info['needed'],
            'Min Budget': f"${info['min']}",
            'Target Budget': f"${info['target']}",
            'Max Budget': f"${info['max']}",
            'Spent': f"${spent_info.get('spent', 0) or 0}",
            'Players': spent_info.get('players', 0) or 0,
            'Strategy': info['strategy'][:50] + '...'
        })

    df = pd.DataFrame(budget_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Total
    total_target = sum(info['target'] for info in BUDGET_STRATEGY.values())
    st.markdown(f"**Total Target Spend:** ${total_target} | **FAAB Reserve:** ${AVAILABLE_BUDGET - total_target}")


if __name__ == "__main__":
    main()
