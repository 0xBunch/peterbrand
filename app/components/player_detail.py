"""BATCAVE - Player Detail Panel Component

Renders a comprehensive slide-out panel with full player context:
- Basic info and projected stats
- Value analysis (PB score, auction value, bid range)
- Historical data (3-year FPTS, past draft prices)
- AI synthesis (contextual analysis from Claude)
"""

import streamlit as st
from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data.database import get_connection
from app.theme import COLORS
from model.inflation import calculate_inflation, get_adjusted_bid_range


def get_player_full_context(player_id: int) -> Optional[dict]:
    """Fetch all available data for a player.

    Returns comprehensive player context for the detail panel.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get base player info + projections
    cursor.execute("""
        SELECT
            p.id, p.name, p.mlb_team, p.positions, p.primary_position,
            proj.fpts, proj.hr, proj.rbi, proj.sb, proj.avg,
            proj.w, proj.sv, proj.k_pitch, proj.era, proj.whip, proj.ip,
            proj.ab, proj.r, proj.h, proj.bb,
            COALESCE(pb.pb_score, 0) as pb_score,
            COALESCE(pb.true_value, 0) as true_value,
            COALESCE(pb.value_gap, 0) as value_gap,
            COALESCE(ab.ab_score, 50) as ab_score,
            COALESCE(ab.auction_value, 1) as auction_value,
            COALESCE(pt.tier, 4) as tier,
            COALESCE(pt.bid_floor, 1) as bid_floor,
            COALESCE(pt.bid_target, 1) as bid_target,
            COALESCE(pt.bid_ceiling, 1) as bid_ceiling
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        LEFT JOIN pb_scores pb ON p.id = pb.player_id
        LEFT JOIN ab_scores ab ON p.id = ab.player_id
        LEFT JOIN position_tiers pt ON p.id = pt.player_id
            AND pt.position = p.primary_position
        WHERE p.id = ?
    """, (player_id,))

    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    # Build base player dict
    is_pitcher = row[4] in ['SP', 'RP']
    player = {
        'id': row[0],
        'name': row[1],
        'mlb_team': row[2] or 'FA',
        'positions': row[3] or '',
        'primary_position': row[4] or 'DH',
        'is_pitcher': is_pitcher,
        'fpts': row[5] or 0,
        'pb_score': row[20],
        'true_value': row[21],
        'value_gap': row[22],
        'ab_score': row[23],
        'auction_value': row[24],
        'tier': row[25],
        'bid_floor': row[26],
        'bid_target': row[27],
        'bid_ceiling': row[28],
    }

    # Add position-specific stats
    if is_pitcher:
        player['stats'] = {
            'W': row[10] or 0,
            'SV': row[11] or 0,
            'K': row[12] or 0,
            'ERA': row[13] or 0,
            'WHIP': row[14] or 0,
            'IP': row[15] or 0,
        }
    else:
        player['stats'] = {
            'HR': row[6] or 0,
            'RBI': row[7] or 0,
            'SB': row[8] or 0,
            'AVG': row[9] or 0,
            'AB': row[16] or 0,
            'R': row[17] or 0,
            'H': row[18] or 0,
            'BB': row[19] or 0,
        }

    # Get historical FPTS
    cursor.execute("""
        SELECT fpts_2023, fpts_2024, fpts_2025, fpts_3ya
        FROM player_history
        WHERE player_id = ?
    """, (player_id,))
    hist_row = cursor.fetchone()
    if hist_row:
        player['history'] = {
            'fpts_2023': hist_row[0],
            'fpts_2024': hist_row[1],
            'fpts_2025': hist_row[2],
            'fpts_3ya': hist_row[3],
        }
    else:
        player['history'] = None

    # Get past draft prices from league history
    cursor.execute("""
        SELECT season, salary, team
        FROM draft_history
        WHERE player_name = ?
        ORDER BY season DESC
        LIMIT 5
    """, (player['name'],))
    draft_hist = cursor.fetchall()
    player['draft_history'] = [
        {'season': r[0], 'salary': r[1], 'team': r[2]}
        for r in draft_hist
    ]

    # Get scouting notes
    cursor.execute("""
        SELECT note, category, created_at
        FROM scouting_notes
        WHERE player_id = ?
        ORDER BY created_at DESC
        LIMIT 3
    """, (player_id,))
    notes = cursor.fetchall()
    player['scouting_notes'] = [
        {'note': n[0], 'category': n[1], 'date': n[2]}
        for n in notes
    ]

    conn.close()
    return player


def render_player_detail_panel(player_id: int, show_ai: bool = True):
    """Render the player detail slide-out panel.

    Args:
        player_id: Database ID of the player
        show_ai: Whether to include AI synthesis section
    """
    player = get_player_full_context(player_id)

    if not player:
        st.error("Player not found")
        return

    # Get inflation-adjusted bid range
    try:
        inflation = calculate_inflation()
        adj_bids = get_adjusted_bid_range(player_id, inflation)
    except Exception:
        inflation = 0
        adj_bids = {
            'floor': player['bid_floor'],
            'target': player['bid_target'],
            'ceiling': player['bid_ceiling'],
            'inflation': 0
        }

    # Header with name and basic info
    st.markdown(f"""
    <div class="detail-header">
        <div style="font-size: 1.5rem; font-weight: 700; color: {COLORS['text']};">
            {player['name']}
        </div>
        <div style="color: {COLORS['text_muted']}; margin-top: 4px;">
            {player['mlb_team']} | {player['positions']}
        </div>
        <div style="margin-top: 8px;">
            <span class="tier-badge tier-{player['tier']}">TIER {player['tier']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Value Analysis Section
    st.markdown('<div class="detail-section-title">💰 VALUE ANALYSIS</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("PB Score", f"{player['pb_score']:.0f}")
        st.metric("Auction Value", f"${player['auction_value']}")
    with col2:
        gap_color = COLORS['positive'] if player['value_gap'] > 0 else COLORS['negative']
        st.metric("Value Gap", f"{'+' if player['value_gap'] > 0 else ''}{player['value_gap']:.0f}")
        st.metric("True Value", f"${player['true_value']:.0f}")

    # Bid Range (with inflation adjustment)
    if inflation != 0:
        st.caption(f"Inflation-adjusted ({inflation*100:+.1f}%)")

    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; padding: 8px; background: {COLORS['panel']}; border-radius: 4px; margin-top: 8px;">
        <div style="text-align: center;">
            <div style="color: {COLORS['text_muted']}; font-size: 0.75rem;">FLOOR</div>
            <div style="color: {COLORS['text']}; font-weight: 600;">${adj_bids['floor']}</div>
        </div>
        <div style="text-align: center;">
            <div style="color: {COLORS['gold']}; font-size: 0.75rem;">TARGET</div>
            <div style="color: {COLORS['gold']}; font-weight: 700; font-size: 1.2rem;">${adj_bids['target']}</div>
        </div>
        <div style="text-align: center;">
            <div style="color: {COLORS['negative']}; font-size: 0.75rem;">MAX</div>
            <div style="color: {COLORS['negative']}; font-weight: 600;">${adj_bids['ceiling']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Projected Stats Section
    st.markdown('<div class="detail-section-title">📊 2026 PROJECTIONS</div>', unsafe_allow_html=True)

    st.metric("Fantasy Points", f"{player['fpts']:.0f}")

    # Display stats based on player type
    stats = player['stats']
    if player['is_pitcher']:
        cols = st.columns(3)
        with cols[0]:
            st.metric("W", stats['W'])
            st.metric("SV", stats['SV'])
        with cols[1]:
            st.metric("K", stats['K'])
            st.metric("IP", f"{stats['IP']:.0f}")
        with cols[2]:
            st.metric("ERA", f"{stats['ERA']:.2f}")
            st.metric("WHIP", f"{stats['WHIP']:.2f}")
    else:
        cols = st.columns(4)
        with cols[0]:
            st.metric("HR", stats['HR'])
        with cols[1]:
            st.metric("RBI", stats['RBI'])
        with cols[2]:
            st.metric("SB", stats['SB'])
        with cols[3]:
            st.metric("AVG", f"{stats['AVG']:.3f}")

    st.markdown("---")

    # Historical Data Section
    if player['history']:
        st.markdown('<div class="detail-section-title">📈 HISTORICAL FPTS</div>', unsafe_allow_html=True)

        hist = player['history']
        hist_cols = st.columns(4)

        with hist_cols[0]:
            fpts_23 = hist['fpts_2023']
            st.metric("2023", f"{fpts_23:.0f}" if fpts_23 else "—")
        with hist_cols[1]:
            fpts_24 = hist['fpts_2024']
            st.metric("2024", f"{fpts_24:.0f}" if fpts_24 else "—")
        with hist_cols[2]:
            fpts_25 = hist['fpts_2025']
            st.metric("2025", f"{fpts_25:.0f}" if fpts_25 else "—")
        with hist_cols[3]:
            avg_3y = hist['fpts_3ya']
            st.metric("3Y Avg", f"{avg_3y:.0f}" if avg_3y else "—")

        st.markdown("---")

    # Draft History Section
    if player['draft_history']:
        st.markdown('<div class="detail-section-title">🏷️ DRAFT HISTORY</div>', unsafe_allow_html=True)

        for dh in player['draft_history']:
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid {COLORS['border']};">
                <span style="color: {COLORS['text_muted']};">{dh['season']}</span>
                <span style="color: {COLORS['text']};">{dh['team']}</span>
                <span style="color: {COLORS['positive']}; font-weight: 600;">${dh['salary']}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

    # Scouting Notes Section
    if player['scouting_notes']:
        st.markdown('<div class="detail-section-title">📝 SCOUTING NOTES</div>', unsafe_allow_html=True)

        for note in player['scouting_notes']:
            st.markdown(f"""
            <div style="background: {COLORS['panel']}; padding: 8px; border-radius: 4px; margin-bottom: 8px;">
                <div style="color: {COLORS['gold']}; font-size: 0.7rem; text-transform: uppercase;">{note['category'] or 'Note'}</div>
                <div style="color: {COLORS['text']}; margin-top: 4px;">{note['note']}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

    # AI Synthesis Section
    if show_ai:
        st.markdown('<div class="detail-section-title">🤖 AI ANALYSIS</div>', unsafe_allow_html=True)

        # Try to get AI analysis
        try:
            from app.ai_assistant import get_draft_advice

            # Build context for AI
            context = {
                'player': player,
                'inflation': inflation,
                'bid_range': adj_bids,
            }

            with st.spinner("Analyzing..."):
                question = f"Quick analysis of {player['name']} for draft. Worth the bid range? Key factors?"
                # This would call Claude - for now show placeholder
                st.markdown(f"""
                <div class="ai-response" style="padding: 12px; background: {COLORS['panel']}; border-radius: 4px; border-left: 3px solid {COLORS['gold']};">
                    <strong>{player['name']}</strong> projects for <strong>{player['fpts']:.0f} FPTS</strong> which places them in <strong>Tier {player['tier']}</strong> at {player['primary_position']}.

                    {"Value gap of +" + str(int(player['value_gap'])) + " suggests market may undervalue." if player['value_gap'] > 5 else ""}
                    {"Value gap of " + str(int(player['value_gap'])) + " suggests market may overpay." if player['value_gap'] < -5 else ""}

                    <br><br>
                    <em style="color: {COLORS['text_muted']};">Target: ${adj_bids['target']}, Max: ${adj_bids['ceiling']}</em>
                </div>
                """, unsafe_allow_html=True)

        except Exception as e:
            st.caption(f"AI analysis unavailable: {e}")


def render_player_quick_view(player_id: int):
    """Render a compact player quick view for inline display."""
    player = get_player_full_context(player_id)

    if not player:
        st.warning("Player not found")
        return

    st.markdown(f"""
    <div style="background: {COLORS['panel']}; padding: 12px; border-radius: 4px; border-left: 3px solid {COLORS['tier' + str(player['tier'])]};">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong style="color: {COLORS['text']};">{player['name']}</strong>
                <span style="color: {COLORS['text_muted']}; margin-left: 8px;">{player['mlb_team']} | {player['positions']}</span>
            </div>
            <div>
                <span style="color: {COLORS['gold']}; font-weight: 700;">PB {player['pb_score']:.0f}</span>
                <span style="margin-left: 12px;">💰 ${player['bid_target']}</span>
            </div>
        </div>
        <div style="margin-top: 8px; color: {COLORS['text_muted']}; font-size: 0.85rem;">
            FPTS: {player['fpts']:.0f} | Tier {player['tier']} | Gap: {'+' if player['value_gap'] > 0 else ''}{player['value_gap']:.0f}
        </div>
    </div>
    """, unsafe_allow_html=True)
