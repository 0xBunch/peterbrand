"""Austin Bats / Peter Brand Theme - Bloomberg Terminal Aesthetic"""

# Color palette - Bloomberg Terminal inspired
COLORS = {
    # Base
    "background": "#0d1117",
    "panel": "#161b22",
    "border": "#30363d",

    # Data colors
    "positive": "#3fb950",
    "negative": "#f85149",
    "alert": "#d29922",
    "link": "#58a6ff",

    # Accent
    "gold": "#c9a227",
    "gold_dim": "#9a7a1c",

    # Text
    "text_primary": "#c9d1d9",
    "text_muted": "#8b949e",

    # Tiers
    "tier1": "#c9a227",  # Gold - Elite
    "tier2": "#8b949e",  # Silver - Solid
    "tier3": "#d29922",  # Amber - Value
    "tier4": "#30363d",  # Gray - Depth
}

CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&display=swap');

    /* === BASE THEME - BLOOMBERG TERMINAL === */
    :root {
        --bg: #0d1117;
        --panel: #161b22;
        --border: #30363d;
        --positive: #3fb950;
        --negative: #f85149;
        --alert: #d29922;
        --link: #58a6ff;
        --gold: #c9a227;
        --text: #c9d1d9;
        --muted: #8b949e;
    }

    .stApp {
        background: var(--bg) !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Hide default Streamlit elements */
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}

    /* === TYPOGRAPHY - MONOSPACE EVERYTHING === */
    * {
        font-family: 'JetBrains Mono', monospace !important;
    }

    h1, h2, h3 {
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
        color: var(--muted) !important;
    }

    p, span, label, .stMarkdown, div {
        color: var(--text) !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px;
    }

    /* === LABELS === */
    label, .stSelectbox label, .stTextInput label, .stNumberInput label {
        font-size: 11px !important;
        font-weight: 500 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        color: var(--muted) !important;
    }

    /* === METRICS - LARGE MONOSPACE NUMBERS === */
    [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 28px !important;
        font-weight: 600 !important;
        color: var(--text) !important;
        letter-spacing: -0.02em;
    }

    [data-testid="stMetricLabel"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 11px !important;
        font-weight: 500 !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: var(--muted) !important;
    }

    [data-testid="stMetricDelta"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 12px !important;
    }

    [data-testid="stMetricDelta"][data-testid-delta-type="positive"] {
        color: var(--positive) !important;
    }

    [data-testid="stMetricDelta"][data-testid-delta-type="negative"] {
        color: var(--negative) !important;
    }

    /* === METRIC CONTAINERS === */
    [data-testid="metric-container"] {
        background: var(--panel);
        border: 1px solid var(--border);
        padding: 12px;
    }

    /* === TABS - TERMINAL STYLE === */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: var(--panel);
        border: 1px solid var(--border);
        border-bottom: none;
        padding: 0;
    }

    .stTabs [data-baseweb="tab"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 11px !important;
        font-weight: 500 !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: var(--muted) !important;
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

    /* === INPUTS - DARK WITH BORDERS === */
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        background: var(--panel) !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
        font-family: 'JetBrains Mono', monospace !important;
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
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px !important;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--gold) !important;
        box-shadow: 0 0 0 1px var(--gold) !important;
    }

    /* === BUTTONS === */
    .stButton > button {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        background: var(--gold) !important;
        color: var(--bg) !important;
        border: none !important;
        border-radius: 0 !important;
        padding: 10px 20px !important;
        transition: all 0.15s ease !important;
    }

    .stButton > button:hover {
        background: #ddb52f !important;
        transform: none;
        box-shadow: 0 0 0 2px var(--gold);
    }

    .stButton > button:active {
        background: #9a7a1c !important;
    }

    /* Primary/Danger button variant */
    .stButton > button[kind="primary"] {
        background: var(--negative) !important;
        color: #ffffff !important;
    }

    .stButton > button[kind="primary"]:hover {
        background: #fa6e5a !important;
        box-shadow: 0 0 0 2px var(--negative);
    }

    /* Secondary button */
    .stButton > button[kind="secondary"] {
        background: transparent !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
    }

    .stButton > button[kind="secondary"]:hover {
        border-color: var(--gold) !important;
        color: var(--gold) !important;
    }

    /* === DATAFRAMES - DENSE DATA TABLES === */
    .stDataFrame {
        font-family: 'JetBrains Mono', monospace !important;
    }

    [data-testid="stDataFrame"] {
        background: var(--panel) !important;
        border: 1px solid var(--border) !important;
    }

    [data-testid="stDataFrame"] > div {
        background: var(--panel) !important;
    }

    /* DataFrame header */
    [data-testid="stDataFrame"] th {
        background: var(--bg) !important;
        color: var(--muted) !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        border-bottom: 1px solid var(--border) !important;
        padding: 8px 12px !important;
    }

    /* DataFrame cells */
    [data-testid="stDataFrame"] td {
        background: var(--panel) !important;
        color: var(--text) !important;
        font-size: 13px !important;
        border-bottom: 1px solid var(--border) !important;
        padding: 6px 12px !important;
    }

    /* Alternating rows */
    [data-testid="stDataFrame"] tr:nth-child(even) td {
        background: #1a2028 !important;
    }

    [data-testid="stDataFrame"] tr:hover td {
        background: #21262d !important;
    }

    /* === SIDEBAR - DARKER PANEL === */
    [data-testid="stSidebar"] {
        background: #0a0d12 !important;
        border-right: 1px solid var(--border);
    }

    [data-testid="stSidebar"] > div:first-child {
        background: #0a0d12 !important;
        padding-top: 16px;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        font-size: 12px !important;
    }

    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
    }

    /* === CONTAINERS === */
    .stContainer, [data-testid="stVerticalBlock"] > div {
        background: transparent;
    }

    /* Panel container */
    .element-container {
        background: transparent;
    }

    /* === EXPANDERS === */
    .streamlit-expanderHeader {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        background: var(--panel) !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
    }

    .streamlit-expanderContent {
        background: var(--panel) !important;
        border: 1px solid var(--border) !important;
        border-top: none !important;
    }

    /* === DIVIDERS === */
    hr {
        border: none;
        height: 1px;
        background: var(--border);
        margin: 16px 0;
    }

    /* === ALERTS === */
    .stAlert {
        background: var(--panel) !important;
        border: 1px solid var(--border) !important;
        border-radius: 0 !important;
        color: var(--text) !important;
        font-size: 13px !important;
    }

    .stSuccess {
        border-left: 3px solid var(--positive) !important;
    }

    .stInfo {
        border-left: 3px solid var(--link) !important;
    }

    .stWarning {
        border-left: 3px solid var(--alert) !important;
    }

    .stError {
        border-left: 3px solid var(--negative) !important;
    }

    /* === CHECKBOXES & RADIO === */
    .stCheckbox > label > span,
    .stRadio > label > span {
        color: var(--text) !important;
        font-size: 13px !important;
    }

    /* === SLIDERS === */
    .stSlider > div > div > div {
        background: var(--border) !important;
    }

    .stSlider > div > div > div > div {
        background: var(--gold) !important;
    }

    .stSlider [data-baseweb="slider"] [data-testid="stThumbValue"] {
        color: var(--gold) !important;
        font-size: 11px !important;
    }

    /* === PROGRESS BAR === */
    .stProgress > div > div {
        background: var(--border) !important;
    }

    .stProgress > div > div > div {
        background: var(--gold) !important;
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
        background: #484f58;
    }

    /* === SPINNERS === */
    .stSpinner > div {
        border-color: var(--gold) !important;
        border-top-color: transparent !important;
    }

    /* === TOAST === */
    [data-testid="stToast"] {
        background: var(--panel) !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
        font-size: 13px !important;
    }

    /* === CUSTOM CLASSES === */

    /* Terminal header with gold accent line */
    .terminal-header {
        background: linear-gradient(90deg, var(--panel) 0%, var(--bg) 100%);
        border-left: 3px solid var(--gold);
        padding: 12px 16px;
        margin-bottom: 16px;
    }

    .terminal-header h1 {
        margin: 0 !important;
        border: none;
        padding: 0;
    }

    /* Data display values */
    .stat-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 24px;
        font-weight: 600;
        color: var(--text);
        letter-spacing: -0.02em;
    }

    .stat-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        font-weight: 500;
        letter-spacing: 0.05em;
        color: var(--muted);
        text-transform: uppercase;
    }

    /* Bid prices */
    .bid-price {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        font-size: 13px;
    }

    .bid-floor { color: var(--muted); }
    .bid-target { color: var(--positive); font-size: 15px; }
    .bid-ceiling { color: var(--negative); }

    /* Player display */
    .player-name {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        font-size: 14px;
        color: var(--text);
    }

    .player-meta {
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        color: var(--muted);
    }

    /* Fantasy points */
    .fpts-value {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        color: var(--positive);
    }

    .fpts-negative {
        color: var(--negative);
    }

    /* Value indicators */
    .value-positive { color: var(--positive); }
    .value-negative { color: var(--negative); }
    .value-neutral { color: var(--muted); }

    /* Tier badges */
    .tier-badge {
        display: inline-block;
        padding: 2px 8px;
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border: 1px solid;
    }

    .tier-1 {
        border-color: #c9a227 !important;
        color: #c9a227 !important;
        background: rgba(201, 162, 39, 0.1);
    }
    .tier-2 {
        border-color: #8b949e !important;
        color: #8b949e !important;
        background: rgba(139, 148, 158, 0.1);
    }
    .tier-3 {
        border-color: #d29922 !important;
        color: #d29922 !important;
        background: rgba(210, 153, 34, 0.1);
    }
    .tier-4 {
        border-color: #30363d !important;
        color: #8b949e !important;
        background: rgba(48, 54, 61, 0.3);
    }

    /* Position badges */
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
    .pos-1B { background: #238636; color: #ffffff; }
    .pos-2B { background: #8957e5; color: #ffffff; }
    .pos-3B { background: #d29922; color: #0d1117; }
    .pos-SS { background: #c9a227; color: #0d1117; }
    .pos-OF { background: #161b22; border: 1px solid #30363d; }
    .pos-DH { background: #30363d; }
    .pos-SP { background: #f85149; color: #ffffff; }
    .pos-RP { background: #da3633; color: #ffffff; }

    /* Player card */
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

    /* Data grid */
    .data-grid {
        display: grid;
        gap: 1px;
        background: var(--border);
    }

    .data-cell {
        background: var(--panel);
        padding: 8px 12px;
        font-size: 13px;
    }

    .data-cell-header {
        background: var(--bg);
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        color: var(--muted);
    }

    /* Status indicators */
    .status-dot {
        display: inline-block;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        margin-right: 6px;
    }

    .status-active { background: var(--positive); }
    .status-pending { background: var(--alert); }
    .status-inactive { background: var(--negative); }
    .status-neutral { background: var(--muted); }

    /* Blinking cursor effect for terminal feel */
    .terminal-cursor::after {
        content: "_";
        animation: blink 1s step-end infinite;
        color: var(--gold);
    }

    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0; }
    }

    /* Page header with branding */
    .page-header {
        background: var(--panel);
        border: 1px solid var(--border);
        border-left: 3px solid var(--gold);
        padding: 16px;
        margin-bottom: 24px;
    }

    .page-header .brand {
        font-size: 14px;
        font-weight: 700;
        color: var(--gold);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .page-header .subtitle {
        font-size: 11px;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }

    /* Market ticker style */
    .ticker {
        background: var(--bg);
        border: 1px solid var(--border);
        padding: 8px 16px;
        display: flex;
        gap: 24px;
        overflow-x: auto;
    }

    .ticker-item {
        display: flex;
        gap: 8px;
        align-items: center;
        white-space: nowrap;
    }

    .ticker-label {
        font-size: 11px;
        color: var(--muted);
        text-transform: uppercase;
    }

    .ticker-value {
        font-size: 13px;
        font-weight: 600;
    }

    /* Tooltip style */
    [data-tooltip] {
        position: relative;
        cursor: help;
    }

    [data-tooltip]:hover::after {
        content: attr(data-tooltip);
        position: absolute;
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%);
        background: var(--bg);
        border: 1px solid var(--border);
        padding: 4px 8px;
        font-size: 11px;
        white-space: nowrap;
        z-index: 1000;
    }
</style>
"""


def inject_theme():
    """Inject the Bloomberg Terminal theme CSS into the Streamlit app."""
    import streamlit as st
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


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


def format_money(value: int) -> str:
    """Format a dollar value with terminal-style formatting."""
    if value >= 0:
        return f"${value:,}"
    else:
        return f"-${abs(value):,}"


def format_fpts(value: float) -> str:
    """Format fantasy points with one decimal."""
    return f"{value:,.1f}"


def value_gap_color(gap: float) -> str:
    """
    Get the appropriate color for a value gap.
    Positive = green (good value), Negative = red (overpay).
    """
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
