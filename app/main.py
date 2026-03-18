"""BATCAVE - Austin Bats Draft Command Center"""
import streamlit as st
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.theme import inject_theme, render_batcave_header, render_sidebar_brand
from app.config import (
    KEEPERS, BUDGET_STRATEGY, AVAILABLE_BUDGET, SALARY_CAP,
    KEEPER_TOTAL, OPPONENTS, ROSTER_SLOTS, NUM_TEAMS
)
from data.database import (
    get_connection, get_undrafted_players, record_draft_pick,
    init_league_teams, add_to_queue, get_queue, clear_drafted_from_queue
)
from model.scarcity import get_scarcity_alerts
from model.inflation import calculate_inflation
from app.components.player_detail import render_player_detail_panel
from app.components.bid_check import render_bid_check

# Page config - must be first Streamlit command
st.set_page_config(
    page_title="BATCAVE",
    page_icon="🦇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject unified theme
inject_theme()


def init_session_state():
    """Initialize session state variables."""
    if 'draft_picks' not in st.session_state:
        st.session_state.draft_picks = []
    if 'my_roster' not in st.session_state:
        # Initialize with keepers
        st.session_state.my_roster = {
            pos: [] for pos in ['C', '1B', '2B', '3B', 'SS', 'OF', 'DH', 'SP', 'RP']
        }
        # Add keepers to roster
        for name, info in KEEPERS.items():
            pos = info['position']
            st.session_state.my_roster[pos].append({
                'name': name,
                'salary': info['salary'],
                'team': info['team'],
                'is_keeper': True
            })
    if 'spent' not in st.session_state:
        st.session_state.spent = 0
    if 'position_filter' not in st.session_state:
        st.session_state.position_filter = 'ALL'
    if 'teams_initialized' not in st.session_state:
        init_league_teams(OPPONENTS)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO league_teams (name, budget_remaining, tendency, notes)
            VALUES ('Austin Bats', ?, 'Your Team', 'Moneyball approach')
        """, (AVAILABLE_BUDGET,))
        conn.commit()
        conn.close()
        st.session_state.teams_initialized = True
    if 'ai_messages' not in st.session_state:
        st.session_state.ai_messages = []
    if 'show_draft_log' not in st.session_state:
        st.session_state.show_draft_log = True
    if 'selected_player' not in st.session_state:
        st.session_state.selected_player = None


def get_pick_count():
    """Get total picks made in draft."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM draft_picks")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_recent_picks(limit=10):
    """Get recent draft picks."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT dp.pick_order, p.name, p.positions, dp.team, dp.salary, dp.is_keeper
        FROM draft_picks dp
        JOIN players p ON dp.player_id = p.id
        ORDER BY dp.pick_order DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_my_spent():
    """Get total spent by Austin Bats."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COALESCE(SUM(salary), 0) FROM draft_picks WHERE team = 'Austin Bats'
    """)
    spent = cursor.fetchone()[0]
    conn.close()
    return spent + KEEPER_TOTAL  # Include keeper salaries


def calculate_round():
    """Estimate current round based on pick count."""
    pick_count = get_pick_count()
    return (pick_count // NUM_TEAMS) + 1


def render_sidebar():
    """Render the sidebar with BATCAVE branding, filters, roster, and needs."""
    with st.sidebar:
        # BATCAVE branding at top
        render_sidebar_brand()

        # Position filter
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-title">POSITION FILTER</div>', unsafe_allow_html=True)

        positions = ['ALL', 'C', '1B', '2B', '3B', 'SS', 'OF', 'DH', 'SP', 'RP']
        selected_pos = st.radio(
            "Position",
            positions,
            index=positions.index(st.session_state.position_filter),
            horizontal=False,
            label_visibility="collapsed"
        )
        if selected_pos != st.session_state.position_filter:
            st.session_state.position_filter = selected_pos
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        # Position needs
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-title">ROSTER NEEDS</div>', unsafe_allow_html=True)

        needs_html = ""
        for pos, strategy in BUDGET_STRATEGY.items():
            needed = strategy['needed']
            target = strategy['target']
            if needed > 0:
                needs_html += f"""
                <div class="roster-slot">
                    <span class="roster-slot-pos">{pos}</span>
                    <span class="need-badge">NEED {needed}</span>
                    <span class="roster-slot-salary">${target}</span>
                </div>
                """
            else:
                needs_html += f"""
                <div class="roster-slot">
                    <span class="roster-slot-pos">{pos}</span>
                    <span class="filled-badge">FILLED</span>
                    <span class="roster-slot-salary">-</span>
                </div>
                """
        st.markdown(needs_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # My Roster
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-title">MY ROSTER</div>', unsafe_allow_html=True)

        roster_html = ""
        for pos in ['C', '1B', '2B', '3B', 'SS', 'OF', 'DH', 'SP', 'RP']:
            players = st.session_state.my_roster.get(pos, [])
            if players:
                for p in players:
                    keeper_mark = "*" if p.get('is_keeper') else ""
                    roster_html += f"""
                    <div class="roster-slot">
                        <span class="roster-slot-pos">{pos}</span>
                        <span class="roster-slot-name">{p['name']}{keeper_mark}</span>
                        <span class="roster-slot-salary">${p['salary']}</span>
                    </div>
                    """
            else:
                needed = ROSTER_SLOTS.get(pos, {}).get('needed', 1)
                if needed > 0:
                    roster_html += f"""
                    <div class="roster-slot">
                        <span class="roster-slot-pos">{pos}</span>
                        <span class="roster-slot-name roster-slot-empty">--- empty ---</span>
                        <span class="roster-slot-salary">-</span>
                    </div>
                    """
        st.markdown(roster_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Draft Queue Panel
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-title">DRAFT QUEUE</div>', unsafe_allow_html=True)

        queue = get_queue()
        clear_drafted_from_queue()  # Auto-remove drafted players

        if queue:
            queue_html = ""
            for q in queue[:8]:  # Show top 8
                max_bid = f"MAX ${q['max_bid']}" if q['max_bid'] else ""
                queue_html += f"""
                <div class="roster-slot">
                    <span class="roster-slot-pos">{q['primary_position'] or '?'}</span>
                    <span class="roster-slot-name">{q['name']}</span>
                    <span class="roster-slot-salary">{max_bid}</span>
                </div>
                """
            st.markdown(queue_html, unsafe_allow_html=True)
        else:
            st.caption("No players queued. Click +Q on player rows.")

        st.markdown('</div>', unsafe_allow_html=True)

        # Scarcity Alerts Panel
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-title">SCARCITY ALERTS</div>', unsafe_allow_html=True)

        current_round = calculate_round()
        alerts = get_scarcity_alerts(current_round)

        if alerts:
            for alert in alerts[:4]:  # Show top 4 alerts
                level_class = "need-badge" if alert['level'] == 'CRITICAL' else "filled-badge"
                st.markdown(f"""
                <div class="roster-slot">
                    <span class="{level_class}">{alert['level']}</span>
                    <span class="roster-slot-name">{alert['position']}: {alert['undrafted']} left</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("No urgent scarcity alerts")

        st.markdown('</div>', unsafe_allow_html=True)


def render_player_table():
    """Render the dense player data table."""
    position = st.session_state.position_filter
    if position == 'ALL':
        position = None

    players = get_undrafted_players(position)

    # Sort by PB Score (descending), fallback to FPTS
    players = sorted(
        players,
        key=lambda x: (x.get('pb_score') or 0, x.get('fpts') or 0),
        reverse=True
    )

    # Table header
    st.markdown("""
    <div class="player-row header">
        <div>PLAYER</div>
        <div>POS</div>
        <div>FPTS</div>
        <div>PB</div>
        <div>TIER</div>
        <div>BID</div>
        <div>MAX</div>
        <div>GAP</div>
    </div>
    """, unsafe_allow_html=True)

    # Create a container for the table with max height
    table_container = st.container()

    with table_container:
        # Display players
        for i, player in enumerate(players[:50]):  # Limit to top 50 for performance
            name = player.get('name', 'Unknown')
            team = player.get('mlb_team', '???')
            positions = player.get('positions', '-')
            fpts = player.get('fpts') or 0
            pb_score = player.get('pb_score') or 0
            tier = player.get('tier') or 4
            bid_floor = player.get('bid_floor') or 1
            bid_target = player.get('bid_target') or 1
            bid_ceiling = player.get('bid_ceiling') or 1
            value_gap = player.get('value_gap') or 0
            player_id = player.get('id')

            # Calculate max_bid if not in data
            max_bid = player.get('max_bid') or min(int(bid_ceiling * 1.25), 50)

            # Value gap color
            if value_gap > 5:
                gap_class = "value-positive"
                gap_display = f"+{value_gap:.0f}"
            elif value_gap < -5:
                gap_class = "value-negative"
                gap_display = f"{value_gap:.0f}"
            else:
                gap_class = "value-neutral"
                gap_display = f"{value_gap:.0f}" if value_gap else "-"

            # Tier badge
            tier_class = f"tier-{tier}" if tier in [1, 2, 3, 4] else "tier-4"

            # Create unique key for each player - 4 columns: data, view, draft, queue
            col1, col2, col3, col4 = st.columns([8, 1, 1, 1])

            with col1:
                st.markdown(f"""
                <div class="player-row" id="player-{player_id}">
                    <div>
                        <span class="player-name">{name}</span>
                        <span class="player-team">{team}</span>
                    </div>
                    <div>{positions}</div>
                    <div>{fpts:.0f}</div>
                    <div>{pb_score:.0f}</div>
                    <div><span class="tier-badge {tier_class}">T{tier}</span></div>
                    <div>${bid_floor}-{bid_target}-{bid_ceiling}</div>
                    <div>${max_bid}</div>
                    <div class="{gap_class}">{gap_display}</div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                if st.button("👁", key=f"view_{player_id}", help=f"View {name} details"):
                    st.session_state.selected_player = player_id
                    st.session_state.selected_player_data = player

            with col3:
                if st.button("D", key=f"draft_{player_id}", help=f"Draft {name}"):
                    st.session_state.drafting_player = player
                    st.session_state.show_draft_modal = True

            with col4:
                if st.button("+Q", key=f"queue_{player_id}", help=f"Add {name} to queue"):
                    add_to_queue(player_id, max_bid=max_bid)
                    st.rerun()


def render_draft_modal():
    """Render draft pick modal if triggered."""
    if st.session_state.get('show_draft_modal') and st.session_state.get('drafting_player'):
        player = st.session_state.drafting_player

        with st.expander(f"🦇 DRAFT: {player['name']}", expanded=True):
            # Get budget info for bid check
            spent = get_my_spent()
            budget_remaining = SALARY_CAP - spent

            # Check if position is needed
            pos = player.get('primary_position', 'DH')
            position_needed = BUDGET_STRATEGY.get(pos, {}).get('needed', 0) > 0

            # Two column layout: bid check + input
            col_check, col_input = st.columns([2, 1])

            with col_check:
                bid_target = player.get('bid_target') or 1

                # Get salary input value (use session state if available)
                current_bid = st.session_state.get('draft_salary', bid_target)

                # Render bid check
                render_bid_check(
                    player=player,
                    current_bid=current_bid,
                    budget_remaining=budget_remaining,
                    position_needed=position_needed,
                    show_ai=True
                )

            with col_input:
                teams = ['Austin Bats'] + list(OPPONENTS.keys())
                team = st.selectbox("Team", teams, key="draft_team")

                salary = st.number_input(
                    "Salary",
                    min_value=1,
                    max_value=100,
                    value=bid_target,
                    key="draft_salary"
                )

                st.markdown("---")

                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("✓ CONFIRM", type="primary", key="confirm_draft", use_container_width=True):
                        record_draft_pick(player['id'], team, salary, is_keeper=False)

                        # Update local roster if it's our pick
                        if team == 'Austin Bats':
                            if pos not in st.session_state.my_roster:
                                st.session_state.my_roster[pos] = []
                            st.session_state.my_roster[pos].append({
                                'name': player['name'],
                                'salary': salary,
                                'team': player.get('mlb_team', '???'),
                                'is_keeper': False
                            })

                        st.session_state.show_draft_modal = False
                        st.session_state.drafting_player = None
                        st.toast(f"✓ {player['name']} drafted by {team} for ${salary}")
                        st.rerun()

                with col_cancel:
                    if st.button("✗ Cancel", key="cancel_draft", use_container_width=True):
                        st.session_state.show_draft_modal = False
                        st.session_state.drafting_player = None
                        st.rerun()


def render_draft_log():
    """Render the collapsible draft log."""
    with st.expander("📋 DRAFT LOG", expanded=st.session_state.show_draft_log):
        recent = get_recent_picks(15)

        if recent:
            st.markdown('<div class="draft-log">', unsafe_allow_html=True)
            for pick in recent:
                pick_num, name, positions, team, salary, is_keeper = pick
                keeper_mark = "*" if is_keeper else ""

                st.markdown(f"""
                <div class="draft-pick">
                    <span class="pick-num">#{pick_num}</span>
                    <span class="pick-player">{name}{keeper_mark}</span>
                    <span class="pick-team">{team}</span>
                    <span class="pick-salary">${salary}</span>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No picks recorded yet. Click D on a player row to record a draft pick.")


def get_ai_context() -> dict:
    """Build context dict for AI from current draft state."""
    spent = get_my_spent()
    remaining = SALARY_CAP - spent

    # Get position needs
    needs = []
    for pos, strategy in BUDGET_STRATEGY.items():
        if strategy['needed'] > 0:
            needs.append(pos)

    # Get current roster
    roster = []
    for pos, players in st.session_state.my_roster.items():
        for p in players:
            roster.append({
                'name': p['name'],
                'position': pos,
                'salary': p['salary']
            })

    return {
        'budget': remaining,
        'needs': needs,
        'roster': roster,
        'round': calculate_round(),
        'league_info': f"12-team H2H points league, {SALARY_CAP} budget"
    }


def render_ai_panel():
    """Render the AI analyst chat panel."""
    with st.expander("🤖 AI ANALYST", expanded=False):
        st.markdown('<div class="ai-panel">', unsafe_allow_html=True)

        # Display previous messages
        for msg in st.session_state.ai_messages[-5:]:  # Show last 5 messages
            role = msg.get('role', 'user')
            content = msg.get('content', '')

            if role == 'user':
                st.markdown(f"**You:** {content}")
            else:
                st.markdown(f'<div class="ai-response">{content}</div>', unsafe_allow_html=True)

        # Chat input
        user_input = st.text_input(
            "Ask about draft strategy, player comparisons, or value picks...",
            key="ai_input",
            label_visibility="collapsed",
            placeholder="e.g., Should I bid $25 on Soto?"
        )

        if user_input:
            st.session_state.ai_messages.append({'role': 'user', 'content': user_input})

            # Try to get AI response
            try:
                from app.ai_assistant import get_draft_advice
                context = get_ai_context()
                response = get_draft_advice(context, user_input)
            except Exception as e:
                response = f"[AI Offline] {str(e)[:100]}"

            st.session_state.ai_messages.append({'role': 'assistant', 'content': response})
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)


def main():
    """Main BATCAVE dashboard entry point."""
    init_session_state()

    # Calculate current inflation
    try:
        inflation = calculate_inflation()
    except Exception:
        inflation = 0

    # Render BATCAVE header
    spent = get_my_spent()
    current_round = calculate_round()
    pick_count = get_pick_count()
    render_batcave_header(
        budget=SALARY_CAP,
        spent=spent,
        round_num=current_round,
        pick_count=pick_count,
        inflation=inflation
    )

    # Render sidebar
    render_sidebar()

    # Main content area
    st.markdown("---")

    # Draft modal (if active)
    render_draft_modal()

    # Check if player detail panel should be shown
    if st.session_state.get('selected_player'):
        # Two-column layout: player table + detail panel
        col_table, col_detail = st.columns([2, 1])

        with col_table:
            render_player_table()

        with col_detail:
            st.markdown("### Player Details")
            if st.button("✕ Close", key="close_detail"):
                st.session_state.selected_player = None
                st.rerun()
            render_player_detail_panel(st.session_state.selected_player)
    else:
        # Full-width player table
        render_player_table()

    st.markdown("---")

    # Bottom panels in columns
    col1, col2 = st.columns([1, 1])

    with col1:
        render_draft_log()

    with col2:
        render_ai_panel()


if __name__ == "__main__":
    main()
