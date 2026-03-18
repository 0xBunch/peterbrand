"""Austin Bats Draft Portal - Bloomberg Terminal Style Dashboard"""
import streamlit as st
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.theme import inject_theme
from app.config import (
    KEEPERS, BUDGET_STRATEGY, AVAILABLE_BUDGET, SALARY_CAP,
    KEEPER_TOTAL, OPPONENTS, ROSTER_SLOTS, NUM_TEAMS
)
from data.database import (
    get_connection, get_undrafted_players, record_draft_pick,
    init_league_teams
)

# Page config - must be first Streamlit command
st.set_page_config(
    page_title="Austin Bats",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject theme
inject_theme()

# Bloomberg-style CSS overrides for extreme density
st.markdown("""
<style>
    /* Ultra-dense Bloomberg aesthetic */
    .stApp {
        background: #0a0e14 !important;
    }

    /* Header bar */
    .header-bar {
        background: linear-gradient(90deg, #0a1628 0%, #132238 100%);
        border-bottom: 1px solid #1e3a5f;
        padding: 8px 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-family: 'JetBrains Mono', monospace;
        margin: -1rem -1rem 1rem -1rem;
    }

    .header-brand {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 1.8rem;
        color: #f5f0e8;
        letter-spacing: 0.1em;
    }

    .header-brand span {
        color: #d4a746;
        font-size: 0.9rem;
        margin-left: 8px;
    }

    .header-stats {
        display: flex;
        gap: 24px;
        font-size: 0.85rem;
    }

    .header-stat {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
    }

    .header-stat-label {
        color: #6b7280;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .header-stat-value {
        color: #4ade80;
        font-weight: 600;
        font-size: 1.1rem;
    }

    .header-stat-value.warning {
        color: #fbbf24;
    }

    /* Dense data table */
    .player-row {
        display: grid;
        grid-template-columns: 2fr 0.5fr 0.7fr 0.7fr 0.7fr 0.6fr 0.8fr 0.6fr;
        gap: 4px;
        padding: 6px 8px;
        border-bottom: 1px solid #1e2d3d;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        align-items: center;
        cursor: pointer;
        transition: background 0.1s;
    }

    .player-row:hover {
        background: #132238;
    }

    .player-row.header {
        background: #0d1926;
        color: #6b7280;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        cursor: default;
        position: sticky;
        top: 0;
        z-index: 10;
    }

    .player-name {
        color: #f5f0e8;
        font-weight: 500;
    }

    .player-team {
        color: #6b7280;
        font-size: 0.7rem;
    }

    .value-positive {
        color: #4ade80;
        font-weight: 600;
    }

    .value-negative {
        color: #f87171;
        font-weight: 600;
    }

    .value-neutral {
        color: #9ca3af;
    }

    .tier-badge {
        display: inline-block;
        padding: 1px 4px;
        font-size: 0.65rem;
        border-radius: 2px;
        font-weight: 600;
    }

    .tier-1 { background: #d4a746; color: #0a0e14; }
    .tier-2 { background: #8a9ba8; color: #0a0e14; }
    .tier-3 { background: #b87333; color: #0a0e14; }
    .tier-4 { background: #4a5568; color: #f5f0e8; }

    /* Sidebar density */
    [data-testid="stSidebar"] {
        background: #0d1117 !important;
        padding-top: 0;
    }

    [data-testid="stSidebar"] .block-container {
        padding-top: 1rem;
    }

    .sidebar-section {
        background: #0a1628;
        border: 1px solid #1e3a5f;
        border-radius: 4px;
        padding: 10px;
        margin-bottom: 12px;
    }

    .sidebar-title {
        color: #d4a746;
        font-family: 'Bebas Neue', sans-serif;
        font-size: 0.9rem;
        letter-spacing: 0.1em;
        margin-bottom: 8px;
        padding-bottom: 4px;
        border-bottom: 1px solid #1e3a5f;
    }

    .roster-slot {
        display: flex;
        justify-content: space-between;
        padding: 4px 0;
        font-size: 0.75rem;
        font-family: 'JetBrains Mono', monospace;
        border-bottom: 1px solid #0d1926;
    }

    .roster-slot-pos {
        color: #6b7280;
        width: 24px;
    }

    .roster-slot-name {
        color: #f5f0e8;
        flex-grow: 1;
        padding-left: 8px;
    }

    .roster-slot-empty {
        color: #4a5568;
        font-style: italic;
    }

    .roster-slot-salary {
        color: #4ade80;
    }

    /* Draft log */
    .draft-log {
        background: #0a1628;
        border: 1px solid #1e3a5f;
        border-radius: 4px;
        max-height: 200px;
        overflow-y: auto;
    }

    .draft-pick {
        display: grid;
        grid-template-columns: 0.3fr 1.5fr 1fr 0.5fr;
        gap: 4px;
        padding: 4px 8px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        border-bottom: 1px solid #0d1926;
    }

    .pick-num {
        color: #6b7280;
    }

    .pick-player {
        color: #f5f0e8;
    }

    .pick-team {
        color: #9ca3af;
    }

    .pick-salary {
        color: #4ade80;
        text-align: right;
    }

    /* AI Panel */
    .ai-panel {
        background: #0a1628;
        border: 1px solid #1e3a5f;
        border-radius: 4px;
        padding: 12px;
    }

    .ai-header {
        color: #d4a746;
        font-family: 'Bebas Neue', sans-serif;
        font-size: 1rem;
        letter-spacing: 0.1em;
        margin-bottom: 8px;
    }

    .ai-response {
        color: #9ca3af;
        font-size: 0.8rem;
        line-height: 1.4;
        font-family: 'IBM Plex Sans', sans-serif;
    }

    /* Position filter buttons */
    .pos-filter {
        display: inline-block;
        padding: 4px 8px;
        margin: 2px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        background: #132238;
        border: 1px solid #1e3a5f;
        border-radius: 2px;
        color: #9ca3af;
        cursor: pointer;
        transition: all 0.1s;
    }

    .pos-filter:hover {
        border-color: #d4a746;
        color: #f5f0e8;
    }

    .pos-filter.active {
        background: #d4a746;
        color: #0a0e14;
        border-color: #d4a746;
    }

    /* Reduce default padding */
    .block-container {
        padding: 1rem 1rem 1rem 1rem !important;
        max-width: none !important;
    }

    /* Hide streamlit branding */
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}

    /* Compact expanders */
    .streamlit-expanderHeader {
        font-size: 0.85rem !important;
        padding: 8px 12px !important;
        background: #0a1628 !important;
    }

    /* Needs indicator */
    .need-badge {
        display: inline-block;
        background: #c41e3a;
        color: #f5f0e8;
        padding: 2px 6px;
        border-radius: 2px;
        font-size: 0.7rem;
        font-weight: 600;
    }

    .filled-badge {
        display: inline-block;
        background: #2d5016;
        color: #f5f0e8;
        padding: 2px 6px;
        border-radius: 2px;
        font-size: 0.7rem;
    }
</style>
""", unsafe_allow_html=True)


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
    # Rough estimate: picks / teams
    return (pick_count // NUM_TEAMS) + 1


def render_header():
    """Render the Bloomberg-style header bar."""
    spent = get_my_spent()
    remaining = SALARY_CAP - spent
    current_round = calculate_round()
    pick_count = get_pick_count()

    st.markdown(f"""
    <div class="header-bar">
        <div>
            <span class="header-brand">AUSTIN BATS <span>powered by Peter Brand</span></span>
        </div>
        <div class="header-stats">
            <div class="header-stat">
                <span class="header-stat-label">Budget</span>
                <span class="header-stat-value {'warning' if remaining < 50 else ''}">${remaining}</span>
            </div>
            <div class="header-stat">
                <span class="header-stat-label">Spent</span>
                <span class="header-stat-value">${spent}</span>
            </div>
            <div class="header-stat">
                <span class="header-stat-label">Round</span>
                <span class="header-stat-value">{current_round}</span>
            </div>
            <div class="header-stat">
                <span class="header-stat-label">Picks</span>
                <span class="header-stat-value">{pick_count}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar():
    """Render the sidebar with filters, roster, and needs."""
    with st.sidebar:
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
        <div>3YA</div>
        <div>PB</div>
        <div>TIER</div>
        <div>BID</div>
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
            fpts_3ya = player.get('fpts_3ya') or 0
            pb_score = player.get('pb_score') or 0
            tier = player.get('tier') or 4
            bid_floor = player.get('bid_floor') or 1
            bid_target = player.get('bid_target') or 1
            bid_ceiling = player.get('bid_ceiling') or 1
            value_gap = player.get('value_gap') or 0
            player_id = player.get('id')

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

            # Create unique key for each player button
            col1, col2 = st.columns([10, 1])

            with col1:
                st.markdown(f"""
                <div class="player-row" id="player-{player_id}">
                    <div>
                        <span class="player-name">{name}</span>
                        <span class="player-team">{team}</span>
                    </div>
                    <div>{positions}</div>
                    <div>{fpts:.0f}</div>
                    <div>{fpts_3ya:.0f}</div>
                    <div>{pb_score:.0f}</div>
                    <div><span class="tier-badge {tier_class}">T{tier}</span></div>
                    <div>${bid_floor}-{bid_target}-{bid_ceiling}</div>
                    <div class="{gap_class}">{gap_display}</div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                if st.button("", key=f"draft_{player_id}", help=f"Draft {name}"):
                    st.session_state.drafting_player = player
                    st.session_state.show_draft_modal = True


def render_draft_modal():
    """Render draft pick modal if triggered."""
    if st.session_state.get('show_draft_modal') and st.session_state.get('drafting_player'):
        player = st.session_state.drafting_player

        with st.expander(f"DRAFT: {player['name']}", expanded=True):
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                teams = ['Austin Bats'] + list(OPPONENTS.keys())
                team = st.selectbox("Team", teams, key="draft_team")

            with col2:
                bid_target = player.get('bid_target') or 1
                salary = st.number_input(
                    "Salary",
                    min_value=1,
                    max_value=100,
                    value=bid_target,
                    key="draft_salary"
                )

            with col3:
                st.write("")  # Spacer
                st.write("")
                if st.button("CONFIRM", type="primary", key="confirm_draft"):
                    record_draft_pick(player['id'], team, salary, is_keeper=False)

                    # Update local roster if it's our pick
                    if team == 'Austin Bats':
                        pos = player.get('primary_position', 'DH')
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
                    st.rerun()

                if st.button("Cancel", key="cancel_draft"):
                    st.session_state.show_draft_modal = False
                    st.session_state.drafting_player = None
                    st.rerun()


def render_draft_log():
    """Render the collapsible draft log."""
    with st.expander("DRAFT LOG", expanded=st.session_state.show_draft_log):
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
            st.info("No picks recorded yet. Click a player row to record a draft pick.")


def render_ai_panel():
    """Render the AI analyst chat panel."""
    with st.expander("AI ANALYST", expanded=False):
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
            placeholder="e.g., Who's the best 3B value right now?"
        )

        if user_input:
            st.session_state.ai_messages.append({'role': 'user', 'content': user_input})

            # Placeholder response - integrate with ai_assistant.py when available
            response = f"[AI module not loaded] Analyzing: '{user_input}' - Check position tiers and PB scores for value plays."
            st.session_state.ai_messages.append({'role': 'assistant', 'content': response})
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)


def main():
    """Main dashboard entry point."""
    init_session_state()

    # Render header
    render_header()

    # Render sidebar
    render_sidebar()

    # Main content area
    st.markdown("---")

    # Draft modal (if active)
    render_draft_modal()

    # Player table
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
