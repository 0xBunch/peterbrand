"""BATCAVE Theme - Austin Bats Draft Assistant"""

import streamlit as st

# Unified color palette - single source of truth
COLORS = {
    # Base backgrounds
    "bg": "#0d1117",
    "bg_dark": "#0a0d12",
    "panel": "#161b22",
    "panel_alt": "#1a2028",

    # Borders
    "border": "#30363d",
    "border_light": "#484f58",

    # Semantic colors
    "positive": "#3fb950",
    "negative": "#f85149",
    "warning": "#d29922",
    "info": "#58a6ff",

    # Brand accent
    "gold": "#c9a227",
    "gold_bright": "#d4a746",
    "gold_dim": "#9a7a1c",

    # Text
    "text": "#c9d1d9",
    "text_muted": "#8b949e",
    "text_dim": "#6b7280",

    # Tiers (consistent across app)
    "tier1": "#c9a227",  # Gold - Elite
    "tier2": "#8b949e",  # Silver - Solid
    "tier3": "#d29922",  # Amber - Value
    "tier4": "#30363d",  # Gray - Depth
}

# Tier display helpers
def tier_color(tier: int) -> str:
    """Get the color for a tier."""
    return {
        1: COLORS["tier1"],
        2: COLORS["tier2"],
        3: COLORS["tier3"],
        4: COLORS["tier4"],
    }.get(tier, COLORS["tier4"])


def tier_name(tier: int) -> str:
    """Get the display name for a tier."""
    return {
        1: "ELITE",
        2: "SOLID",
        3: "VALUE",
        4: "DEPTH",
    }.get(tier, "DEPTH")


# Formatting helpers
def format_money(value: int) -> str:
    """Format a dollar value."""
    if value >= 0:
        return f"${value:,}"
    else:
        return f"-${abs(value):,}"


def format_fpts(value: float) -> str:
    """Format fantasy points with one decimal."""
    return f"{value:,.1f}"


def value_gap_color(gap: float) -> str:
    """Get color for a value gap. Positive = green, Negative = red."""
    if gap > 0:
        return COLORS["positive"]
    elif gap < 0:
        return COLORS["negative"]
    else:
        return COLORS["text_muted"]


def format_value_gap(gap: float) -> str:
    """Format a value gap with color-coded HTML."""
    color = value_gap_color(gap)
    sign = "+" if gap > 0 else ""
    return f'<span style="color: {color}; font-family: JetBrains Mono, monospace;">{sign}${gap:,.0f}</span>'


# Complete CSS for the application
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&display=swap');

    /* === CSS VARIABLES === */
    :root {
        --bg: #0d1117;
        --bg-dark: #0a0d12;
        --panel: #161b22;
        --panel-alt: #1a2028;
        --border: #30363d;
        --border-light: #484f58;
        --positive: #3fb950;
        --negative: #f85149;
        --warning: #d29922;
        --info: #58a6ff;
        --gold: #c9a227;
        --gold-bright: #d4a746;
        --gold-dim: #9a7a1c;
        --text: #c9d1d9;
        --text-muted: #8b949e;
        --text-dim: #6b7280;
        --tier1: #c9a227;
        --tier2: #8b949e;
        --tier3: #d29922;
        --tier4: #30363d;
    }

    /* === BASE RESET === */
    .stApp {
        background: var(--bg) !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    * {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Hide Streamlit branding */
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}

    /* === TYPOGRAPHY === */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
        color: var(--text) !important;
        text-transform: uppercase;
    }

    h1 {
        font-size: 14px !important;
        border-bottom: 2px solid var(--gold);
        padding-bottom: 8px;
        margin-bottom: 16px !important;
    }

    h1::before {
        content: "▸ ";
        color: var(--gold);
    }

    h2 {
        font-size: 14px !important;
        font-weight: 600 !important;
        color: var(--gold) !important;
        border-left: 3px solid var(--gold);
        padding-left: 8px;
        margin: 16px 0 8px 0 !important;
    }

    h3 {
        font-size: 13px !important;
        font-weight: 500 !important;
        color: var(--text-muted) !important;
    }

    p, span, label, .stMarkdown, div {
        color: var(--text) !important;
        font-size: 13px;
    }

    /* === LABELS === */
    label, .stSelectbox label, .stTextInput label, .stNumberInput label {
        font-size: 11px !important;
        font-weight: 500 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        color: var(--text-muted) !important;
    }

    /* === METRICS === */
    [data-testid="stMetricValue"] {
        font-size: 28px !important;
        font-weight: 600 !important;
        color: var(--text) !important;
        letter-spacing: -0.02em;
    }

    [data-testid="stMetricLabel"] {
        font-size: 11px !important;
        font-weight: 500 !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: var(--text-muted) !important;
    }

    [data-testid="stMetricDelta"] {
        font-size: 12px !important;
    }

    [data-testid="metric-container"] {
        background: var(--panel);
        border: 1px solid var(--border);
        padding: 12px;
    }

    /* === BATCAVE HEADER BAR === */
    .batcave-header {
        background: linear-gradient(90deg, var(--panel) 0%, var(--bg) 100%);
        border-bottom: 1px solid var(--border);
        padding: 12px 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: -1rem -1rem 1rem -1rem;
    }

    .batcave-brand {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--gold-bright);
        letter-spacing: 0.15em;
    }

    .batcave-brand .subtitle {
        font-size: 0.7rem;
        color: var(--text-muted);
        letter-spacing: 0.05em;
        margin-left: 12px;
    }

    .batcave-stats {
        display: flex;
        gap: 24px;
        font-size: 0.85rem;
    }

    .batcave-stat {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
    }

    .batcave-stat-label {
        color: var(--text-dim);
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .batcave-stat-value {
        color: var(--positive);
        font-weight: 600;
        font-size: 1.1rem;
    }

    .batcave-stat-value.warning {
        color: var(--warning);
    }

    /* === SIDEBAR === */
    [data-testid="stSidebar"] {
        background: var(--bg-dark) !important;
        border-right: 1px solid var(--border);
    }

    [data-testid="stSidebar"] > div:first-child {
        background: var(--bg-dark) !important;
        padding-top: 8px;
    }

    .sidebar-brand {
        background: var(--panel);
        border: 1px solid var(--border);
        border-left: 3px solid var(--gold);
        padding: 12px 16px;
        margin: 0 0 16px 0;
        text-align: center;
    }

    .sidebar-brand-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: var(--gold-bright);
        letter-spacing: 0.2em;
    }

    .sidebar-section {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 4px;
        padding: 10px;
        margin-bottom: 12px;
    }

    .sidebar-title {
        color: var(--gold);
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        margin-bottom: 8px;
        padding-bottom: 4px;
        border-bottom: 1px solid var(--border);
        text-transform: uppercase;
    }

    .roster-slot {
        display: flex;
        justify-content: space-between;
        padding: 4px 0;
        font-size: 0.75rem;
        border-bottom: 1px solid var(--border);
    }

    .roster-slot:last-child {
        border-bottom: none;
    }

    .roster-slot-pos {
        color: var(--text-dim);
        width: 24px;
    }

    .roster-slot-name {
        color: var(--text);
        flex-grow: 1;
        padding-left: 8px;
    }

    .roster-slot-empty {
        color: var(--border-light);
        font-style: italic;
    }

    .roster-slot-salary {
        color: var(--positive);
    }

    /* === BADGES === */
    .need-badge {
        display: inline-block;
        background: var(--negative);
        color: white;
        padding: 2px 6px;
        border-radius: 2px;
        font-size: 0.65rem;
        font-weight: 600;
    }

    .filled-badge {
        display: inline-block;
        background: #2d5016;
        color: white;
        padding: 2px 6px;
        border-radius: 2px;
        font-size: 0.65rem;
    }

    .tier-badge {
        display: inline-block;
        padding: 2px 6px;
        font-size: 0.65rem;
        border-radius: 2px;
        font-weight: 600;
    }

    .tier-1 { background: var(--tier1); color: var(--bg); }
    .tier-2 { background: var(--tier2); color: var(--bg); }
    .tier-3 { background: var(--tier3); color: var(--bg); }
    .tier-4 { background: var(--tier4); color: var(--text); }

    /* === PLAYER TABLE === */
    .player-row {
        display: grid;
        grid-template-columns: 2fr 0.5fr 0.7fr 0.7fr 0.7fr 0.6fr 0.8fr 0.6fr;
        gap: 4px;
        padding: 6px 8px;
        border-bottom: 1px solid var(--border);
        font-size: 0.8rem;
        align-items: center;
        cursor: pointer;
        transition: background 0.1s;
    }

    .player-row:hover {
        background: var(--panel);
    }

    .player-row.header {
        background: var(--bg-dark);
        color: var(--text-dim);
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        cursor: default;
        position: sticky;
        top: 0;
        z-index: 10;
    }

    .player-name {
        color: var(--text);
        font-weight: 500;
    }

    .player-team {
        color: var(--text-dim);
        font-size: 0.7rem;
    }

    .value-positive { color: var(--positive); font-weight: 600; }
    .value-negative { color: var(--negative); font-weight: 600; }
    .value-neutral { color: var(--text-muted); }

    /* === DRAFT LOG === */
    .draft-log {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 4px;
        max-height: 200px;
        overflow-y: auto;
    }

    .draft-pick {
        display: grid;
        grid-template-columns: 0.3fr 1.5fr 1fr 0.5fr;
        gap: 4px;
        padding: 4px 8px;
        font-size: 0.75rem;
        border-bottom: 1px solid var(--border);
    }

    .draft-pick:last-child {
        border-bottom: none;
    }

    .pick-num { color: var(--text-dim); }
    .pick-player { color: var(--text); }
    .pick-team { color: var(--text-muted); }
    .pick-salary { color: var(--positive); text-align: right; }

    /* === AI PANEL === */
    .ai-panel {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 4px;
        padding: 12px;
    }

    .ai-header {
        color: var(--gold);
        font-size: 0.9rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        margin-bottom: 8px;
        text-transform: uppercase;
    }

    .ai-response {
        color: var(--text-muted);
        font-size: 0.85rem;
        line-height: 1.5;
    }

    /* === INPUTS === */
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        background: var(--panel) !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
        font-size: 13px !important;
    }

    .stSelectbox [data-baseweb="select"] > div {
        background: var(--panel) !important;
        border-color: var(--border) !important;
    }

    .stSelectbox [data-baseweb="select"] > div:focus-within {
        border-color: var(--gold) !important;
        box-shadow: 0 0 0 1px var(--gold) !important;
    }

    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        background: var(--panel) !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
        font-size: 13px !important;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--gold) !important;
        box-shadow: 0 0 0 1px var(--gold) !important;
    }

    /* === BUTTONS === */
    .stButton > button {
        font-size: 11px !important;
        font-weight: 600 !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        background: var(--gold) !important;
        color: var(--bg) !important;
        border: none !important;
        border-radius: 2px !important;
        padding: 10px 20px !important;
        transition: all 0.15s ease !important;
    }

    .stButton > button:hover {
        background: var(--gold-bright) !important;
        box-shadow: 0 0 0 2px var(--gold);
    }

    .stButton > button:active {
        background: var(--gold-dim) !important;
    }

    .stButton > button[kind="primary"] {
        background: var(--positive) !important;
        color: white !important;
    }

    .stButton > button[kind="primary"]:hover {
        background: #4ade80 !important;
        box-shadow: 0 0 0 2px var(--positive);
    }

    .stButton > button[kind="secondary"] {
        background: transparent !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
    }

    .stButton > button[kind="secondary"]:hover {
        border-color: var(--gold) !important;
        color: var(--gold) !important;
    }

    /* === DATAFRAMES === */
    [data-testid="stDataFrame"] {
        background: var(--panel) !important;
        border: 1px solid var(--border) !important;
    }

    [data-testid="stDataFrame"] th {
        background: var(--bg) !important;
        color: var(--text-muted) !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        border-bottom: 1px solid var(--border) !important;
        padding: 8px 12px !important;
    }

    [data-testid="stDataFrame"] td {
        background: var(--panel) !important;
        color: var(--text) !important;
        font-size: 13px !important;
        border-bottom: 1px solid var(--border) !important;
        padding: 6px 12px !important;
    }

    [data-testid="stDataFrame"] tr:nth-child(even) td {
        background: var(--panel-alt) !important;
    }

    [data-testid="stDataFrame"] tr:hover td {
        background: #21262d !important;
    }

    /* === TABS === */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: var(--panel);
        border: 1px solid var(--border);
        border-bottom: none;
        padding: 0;
    }

    .stTabs [data-baseweb="tab"] {
        font-size: 11px !important;
        font-weight: 500 !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: var(--text-muted) !important;
        background: transparent !important;
        border: none !important;
        border-right: 1px solid var(--border) !important;
        border-bottom: 2px solid transparent !important;
        padding: 10px 16px !important;
        min-height: auto !important;
    }

    .stTabs [data-baseweb="tab"]:last-child {
        border-right: none !important;
    }

    .stTabs [aria-selected="true"] {
        color: var(--gold) !important;
        background: var(--bg) !important;
        border-bottom: 2px solid var(--gold) !important;
    }

    .stTabs [data-baseweb="tab-panel"] {
        background: var(--bg);
        border: 1px solid var(--border);
        border-top: none;
        padding: 16px;
    }

    /* === EXPANDERS === */
    .streamlit-expanderHeader {
        font-size: 12px !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        background: var(--panel) !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
        padding: 8px 12px !important;
    }

    .streamlit-expanderContent {
        background: var(--panel) !important;
        border: 1px solid var(--border) !important;
        border-top: none !important;
    }

    /* === ALERTS === */
    .stAlert {
        background: var(--panel) !important;
        border: 1px solid var(--border) !important;
        border-radius: 0 !important;
        color: var(--text) !important;
        font-size: 13px !important;
    }

    .stSuccess { border-left: 3px solid var(--positive) !important; }
    .stInfo { border-left: 3px solid var(--info) !important; }
    .stWarning { border-left: 3px solid var(--warning) !important; }
    .stError { border-left: 3px solid var(--negative) !important; }

    /* === DIVIDERS === */
    hr {
        border: none;
        height: 1px;
        background: var(--border);
        margin: 16px 0;
    }

    /* === REDUCE DEFAULT PADDING === */
    .block-container {
        padding: 1rem 1rem 1rem 1rem !important;
        max-width: none !important;
    }

    /* === SCROLLBAR === */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: var(--bg);
    }

    ::-webkit-scrollbar-thumb {
        background: var(--border);
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--border-light);
    }

    /* === POSITION BADGES === */
    .pos-badge {
        display: inline-block;
        padding: 2px 6px;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 0.03em;
        background: var(--border);
        color: var(--text);
        margin-right: 4px;
    }

    .pos-C { background: #30363d; }
    .pos-1B { background: #238636; color: white; }
    .pos-2B { background: #8957e5; color: white; }
    .pos-3B { background: #d29922; color: var(--bg); }
    .pos-SS { background: #c9a227; color: var(--bg); }
    .pos-OF { background: #161b22; border: 1px solid #30363d; }
    .pos-DH { background: #30363d; }
    .pos-SP { background: #f85149; color: white; }
    .pos-RP { background: #da3633; color: white; }

    /* === PLAYER CARD (for detail panel) === */
    .player-card {
        background: var(--panel);
        border: 1px solid var(--border);
        padding: 12px;
        margin: 4px 0;
        transition: border-color 0.15s ease;
    }

    .player-card:hover {
        border-color: var(--gold);
    }

    /* === INFLATION INDICATOR === */
    .inflation-badge {
        display: inline-block;
        padding: 4px 8px;
        font-size: 0.75rem;
        font-weight: 600;
        border-radius: 2px;
    }

    .inflation-positive {
        background: rgba(248, 81, 73, 0.2);
        color: var(--negative);
        border: 1px solid var(--negative);
    }

    .inflation-negative {
        background: rgba(63, 185, 80, 0.2);
        color: var(--positive);
        border: 1px solid var(--positive);
    }

    .inflation-neutral {
        background: var(--border);
        color: var(--text-muted);
    }

    /* === SLIDE-OUT PANEL (for player details) === */
    .detail-panel {
        background: var(--panel);
        border-left: 1px solid var(--border);
        padding: 16px;
        height: 100%;
        overflow-y: auto;
    }

    .detail-header {
        border-bottom: 2px solid var(--gold);
        padding-bottom: 12px;
        margin-bottom: 16px;
    }

    .detail-section {
        margin-bottom: 16px;
        padding-bottom: 16px;
        border-bottom: 1px solid var(--border);
    }

    .detail-section:last-child {
        border-bottom: none;
    }

    .detail-section-title {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--gold);
        margin-bottom: 8px;
    }

    .stat-row {
        display: flex;
        justify-content: space-between;
        padding: 4px 0;
        font-size: 13px;
    }

    .stat-label {
        color: var(--text-muted);
    }

    .stat-value {
        color: var(--text);
        font-weight: 500;
    }

    /* === BID ADVISOR === */
    .bid-advisor {
        background: linear-gradient(135deg, var(--panel) 0%, var(--bg-dark) 100%);
        border: 1px solid var(--gold-dim);
        border-radius: 4px;
        padding: 16px;
        margin-top: 12px;
    }

    .bid-advisor-header {
        color: var(--gold);
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 8px;
    }

    .bid-recommendation {
        font-size: 1.2rem;
        font-weight: 700;
        margin: 8px 0;
    }

    .bid-recommendation.buy {
        color: var(--positive);
    }

    .bid-recommendation.pass {
        color: var(--negative);
    }

    .bid-recommendation.maybe {
        color: var(--warning);
    }
</style>
"""


def inject_theme():
    """Inject BATCAVE theme CSS into the Streamlit app."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_batcave_header(budget: int, spent: int, round_num: int, pick_count: int, inflation: float = 0):
    """Render the BATCAVE header bar with stats."""
    remaining = budget - spent

    # Inflation display
    if inflation > 0:
        inflation_html = f'<span class="inflation-badge inflation-positive">+{inflation:.0%} INFLATION</span>'
    elif inflation < 0:
        inflation_html = f'<span class="inflation-badge inflation-negative">{inflation:.0%} DEFLATION</span>'
    else:
        inflation_html = '<span class="inflation-badge inflation-neutral">NEUTRAL</span>'

    st.markdown(f"""
    <div class="batcave-header">
        <div>
            <span class="batcave-brand">BATCAVE<span class="subtitle">DRAFT COMMAND CENTER</span></span>
        </div>
        <div class="batcave-stats">
            <div class="batcave-stat">
                <span class="batcave-stat-label">Budget</span>
                <span class="batcave-stat-value {'warning' if remaining < 50 else ''}">${remaining}</span>
            </div>
            <div class="batcave-stat">
                <span class="batcave-stat-label">Spent</span>
                <span class="batcave-stat-value">${spent}</span>
            </div>
            <div class="batcave-stat">
                <span class="batcave-stat-label">Round</span>
                <span class="batcave-stat-value">{round_num}</span>
            </div>
            <div class="batcave-stat">
                <span class="batcave-stat-label">Picks</span>
                <span class="batcave-stat-value">{pick_count}</span>
            </div>
            <div class="batcave-stat">
                {inflation_html}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar_brand():
    """Render BATCAVE branding in sidebar."""
    st.markdown("""
    <div class="sidebar-brand">
        <div class="sidebar-brand-title">BATCAVE</div>
    </div>
    """, unsafe_allow_html=True)
