"""BATCAVE - Bid Check Component

Quick "Should I bid $X on Y?" check that provides:
- Value vs bid comparison
- Position need assessment
- Budget impact analysis
- AI recommendation
"""

import streamlit as st
from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.theme import COLORS
from model.inflation import calculate_inflation, get_adjusted_bid_range


def render_bid_check(
    player: dict,
    current_bid: int,
    budget_remaining: int,
    position_needed: bool = True,
    show_ai: bool = True
):
    """Render a quick bid check panel.

    Args:
        player: Player dict with name, fpts, auction_value, etc.
        current_bid: Current bid amount to evaluate
        budget_remaining: User's remaining budget
        position_needed: Whether user needs this position
        show_ai: Whether to include AI recommendation
    """
    name = player.get('name', 'Unknown')
    position = player.get('primary_position', '?')
    fpts = player.get('fpts', 0)
    auction_value = player.get('auction_value', 1)
    bid_target = player.get('bid_target', 1)
    bid_ceiling = player.get('bid_ceiling', 1)

    # Get inflation-adjusted values
    try:
        inflation = calculate_inflation()
        adj_bids = get_adjusted_bid_range(player.get('id'), inflation)
        adj_target = adj_bids.get('target', bid_target)
        adj_ceiling = adj_bids.get('ceiling', bid_ceiling)
    except Exception:
        inflation = 0
        adj_target = bid_target
        adj_ceiling = bid_ceiling

    # Calculate value difference
    value_diff = adj_target - current_bid
    value_pct = ((adj_target - current_bid) / adj_target * 100) if adj_target > 0 else 0

    # Determine recommendation
    if current_bid <= adj_target * 0.85:
        recommendation = "BUY"
        rec_color = COLORS['positive']
        rec_emoji = "🔥"
        rec_reason = f"Great value! ${abs(value_diff):.0f} below target"
    elif current_bid <= adj_target:
        recommendation = "BID"
        rec_color = COLORS['positive']
        rec_emoji = "✓"
        rec_reason = "At or below target value"
    elif current_bid <= adj_ceiling:
        recommendation = "MAYBE"
        rec_color = COLORS['warning']
        rec_emoji = "⚠️"
        rec_reason = f"${current_bid - adj_target:.0f} over target but within ceiling"
    else:
        recommendation = "PASS"
        rec_color = COLORS['negative']
        rec_emoji = "✗"
        rec_reason = f"${current_bid - adj_ceiling:.0f} over max value"

    # Adjust for position need
    if not position_needed and recommendation in ["MAYBE", "BID"]:
        recommendation = "PASS"
        rec_color = COLORS['negative']
        rec_emoji = "✗"
        rec_reason = f"Don't need {position} - skip this one"

    # Check budget impact
    budget_after = budget_remaining - current_bid
    if budget_after < 10 and recommendation != "PASS":
        rec_reason += " | ⚠️ Low budget after"

    # Render the check
    st.markdown(f"""
    <div class="bid-advisor">
        <div class="bid-advisor-header">{rec_emoji} BID CHECK: {name}</div>

        <div class="bid-recommendation {recommendation.lower()}" style="color: {rec_color};">
            {recommendation}
        </div>

        <div style="color: {COLORS['text_muted']}; margin-bottom: 12px;">
            {rec_reason}
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
            <div style="background: {COLORS['panel']}; padding: 8px; border-radius: 4px;">
                <div style="color: {COLORS['text_muted']}; font-size: 0.7rem;">CURRENT BID</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: {COLORS['text']};">${current_bid}</div>
            </div>
            <div style="background: {COLORS['panel']}; padding: 8px; border-radius: 4px;">
                <div style="color: {COLORS['text_muted']}; font-size: 0.7rem;">TARGET VALUE</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: {COLORS['gold']};">${adj_target}</div>
            </div>
            <div style="background: {COLORS['panel']}; padding: 8px; border-radius: 4px;">
                <div style="color: {COLORS['text_muted']}; font-size: 0.7rem;">MAX BID</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: {COLORS['negative']};">${adj_ceiling}</div>
            </div>
            <div style="background: {COLORS['panel']}; padding: 8px; border-radius: 4px;">
                <div style="color: {COLORS['text_muted']}; font-size: 0.7rem;">BUDGET AFTER</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: {'#f85149' if budget_after < 20 else COLORS['positive']};">${budget_after}</div>
            </div>
        </div>

        <div style="margin-top: 12px; padding: 8px; background: {COLORS['bg']}; border-radius: 4px;">
            <div style="color: {COLORS['text_muted']}; font-size: 0.8rem;">
                FPTS: {fpts:.0f} | Position: {position} {'(NEED)' if position_needed else '(FILLED)'}
                {f' | Inflation: {inflation*100:+.1f}%' if inflation != 0 else ''}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # AI insight if enabled
    if show_ai:
        try:
            from app.ai_assistant import get_value_alert
            with st.spinner("Getting AI take..."):
                ai_response = get_value_alert(player, current_bid)
                st.markdown(f"""
                <div style="margin-top: 8px; padding: 8px; background: {COLORS['panel']}; border-left: 3px solid {COLORS['gold']}; border-radius: 4px;">
                    <span style="color: {COLORS['gold']}; font-size: 0.75rem;">AI:</span>
                    <span style="color: {COLORS['text']};">{ai_response}</span>
                </div>
                """, unsafe_allow_html=True)
        except Exception:
            pass  # AI not available, skip silently

    return recommendation


def quick_bid_buttons(player_id: int, player_name: str, adj_target: int, adj_ceiling: int):
    """Render quick bid action buttons."""
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(f"Draft @ ${adj_target}", key=f"qb_target_{player_id}", use_container_width=True):
            return ('draft', adj_target)

    with col2:
        if st.button(f"Max @ ${adj_ceiling}", key=f"qb_max_{player_id}", use_container_width=True):
            return ('draft', adj_ceiling)

    with col3:
        if st.button("Pass", key=f"qb_pass_{player_id}", use_container_width=True):
            return ('pass', 0)

    return None
