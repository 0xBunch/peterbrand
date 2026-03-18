"""League configuration and scoring rules for Dedeaux Field 4.0"""

# League settings
LEAGUE_NAME = "Dedeaux Field 4.0"
NUM_TEAMS = 10
SALARY_CAP = 320
KEEPER_MAX_SALARY = 30

# Your keepers
KEEPERS = {
    "Nico Hoerner": {"position": "2B", "team": "CHC", "salary": 11, "fpts_proj": 340},
    "CJ Abrams": {"position": "SS", "team": "WAS", "salary": 5, "fpts_proj": 375},
    "Joe Misirowski": {"position": "SP", "team": "MIL", "salary": 5, "fpts_proj": 330},
}
KEEPER_TOTAL = sum(k["salary"] for k in KEEPERS.values())
AVAILABLE_BUDGET = SALARY_CAP - KEEPER_TOTAL

# Target FAAB reserve
FAAB_RESERVE_TARGET = 45
AUCTION_SPENDING_TARGET = AVAILABLE_BUDGET - FAAB_RESERVE_TARGET

# Roster requirements
ROSTER_SLOTS = {
    "C": {"min": 1, "max": 4, "needed": 1},
    "1B": {"min": 1, "max": 5, "needed": 1},
    "2B": {"min": 1, "max": 5, "needed": 0},  # Hoerner
    "3B": {"min": 1, "max": 5, "needed": 1},
    "SS": {"min": 1, "max": 5, "needed": 0},  # Abrams
    "OF": {"min": 3, "max": 7, "needed": 3},
    "DH": {"min": 1, "max": 4, "needed": 1},
    "SP": {"min": 4, "max": 13, "needed": 4},  # 1 keeper
    "RP": {"min": 1, "max": 10, "needed": 2},
}

# Scoring rules (points per stat)
BATTING_SCORING = {
    "1B": 1,
    "2B": 2,
    "3B": 3,
    "HR": 4,
    "R": 1,
    "RBI": 1,
    "BB": 1,
    "SB": 3,
    "HBP": 1,
    "K": -1,
    "CS": -1,
    "E": -2,
}

PITCHING_SCORING = {
    "W": 5,
    "L": -3,
    "S": 5,
    "BS": -3,
    "QS": 3,
    "K": 1,
    "ER": -2,
    "H": -1,
    "BB": -1,
    "HB": -1,
    "OUT": 1,  # 1 point per out (IP * 3)
}

# Positional scarcity scores (from AB Score formula)
POSITIONAL_SCARCITY = {
    "3B": {"score": 100, "gap": 248, "replacement_fpts": 309},
    "OF": {"score": 95, "gap": 234, "replacement_fpts": 334},
    "SP": {"score": 94, "gap": 233, "replacement_fpts": 354},
    "2B": {"score": 83, "gap": 206, "replacement_fpts": 270},
    "SS": {"score": 60, "gap": 148, "replacement_fpts": 383},
    "1B": {"score": 51, "gap": 127, "replacement_fpts": 355},
    "DH": {"score": 40, "gap": 98, "replacement_fpts": 476},
    "C": {"score": 39, "gap": 96, "replacement_fpts": 248},
    "RP": {"score": 35, "gap": 87, "replacement_fpts": 290},
}

# Team quality tiers (2026 projections)
TEAM_QUALITY = {
    # Contenders (73-100)
    "LAD": 100, "NYM": 95, "BAL": 92, "PHI": 90, "BOS": 88,
    "HOU": 87, "SEA": 85, "ATL": 84, "KC": 82, "SF": 80,
    "DET": 78, "CLE": 77, "MIL": 76, "ARI": 75, "SD": 74, "NYY": 73,
    # Mid-tier (55-68)
    "TOR": 68, "CIN": 65, "MIN": 63, "TEX": 60, "CHC": 58,
    "PIT": 57, "STL": 56, "LAA": 55, "TB": 55,
    # Rebuilders (25-45)
    "WAS": 45, "MIA": 40, "OAK": 35, "ATH": 35, "CHW": 30, "COL": 25,
}

# Budget allocation strategy
BUDGET_STRATEGY = {
    "C": {"min": 3, "max": 8, "target": 5, "needed": 1, "strategy": "Wait for value, catcher runs shallow"},
    "1B": {"min": 15, "max": 25, "target": 20, "needed": 1, "strategy": "Mid-tier, don't overpay for ceiling"},
    "2B": {"min": 0, "max": 0, "target": 0, "needed": 0, "strategy": "LOCKED (Hoerner)"},
    "3B": {"min": 20, "max": 35, "target": 28, "needed": 1, "strategy": "Scarcest position, pay up if needed"},
    "SS": {"min": 0, "max": 0, "target": 0, "needed": 0, "strategy": "LOCKED (Abrams)"},
    "OF": {"min": 55, "max": 75, "target": 65, "needed": 3, "strategy": "1 elite ($40-50) + 2 value ($5-15 each)"},
    "DH": {"min": 3, "max": 10, "target": 6, "needed": 1, "strategy": "Deep position, find value late"},
    "SP": {"min": 60, "max": 80, "target": 70, "needed": 4, "strategy": "Spread across tiers, IL stashes"},
    "RP": {"min": 5, "max": 15, "target": 10, "needed": 2, "strategy": "Closers volatile, target value"},
}

# Opponent tendencies
OPPONENTS = {
    "Bushwood CC": {"style": "Balanced", "tendency": "Spreads $20+ across 6 players"},
    "Cardinal and Gold": {"style": "Pitching whale", "tendency": "50% budget on pitching, drives up SP"},
    "Ireland": {"style": "Upside chaser", "tendency": "Pays premium for young SS/OF"},
    "MeShe": {"style": "Elite bat + arm", "tendency": "Anchors with 1 stud hitter + 1 stud SP"},
    "Moneyball Dos": {"style": "Value hunter", "tendency": "Smartest drafter, finds $1 steals"},
    "Sarre": {"style": "Pitching heavy", "tendency": "Buys 3-4 SP aggressively, huge FAAB"},
    "Sofa Kings": {"style": "Star-chaser", "tendency": "Spends $50 on elite SS"},
    "Swing and a Miss 2020": {"style": "Stars & scrubs", "tendency": "$50 on Elly, 12 players at $1"},
    "The Mike Uhlenkamp Experience": {"style": "OF chaser", "tendency": "Chases elite OF ceiling regardless of injury"},
}

# Default AB Score weights
DEFAULT_WEIGHTS = {
    "scarcity": 0.25,
    "slot": 0.20,
    "fpts": 0.18,
    "durability": 0.14,
    "team_quality": 0.10,
    "multi_pos": 0.08,
    "value_gap": 0.05,
    # New components (R1)
    "health": 0.00,  # Will enable in model tuning
    "contract": 0.00,  # Will enable in model tuning
}

# Tier FPTS cutoffs by position (will be calculated from data)
# These are approximate starting points
TIER_CUTOFFS = {
    "C": [350, 280, 220],  # Tier 1 > 350, Tier 2 > 280, Tier 3 > 220, else Tier 4
    "1B": [450, 380, 320],
    "2B": [420, 350, 290],
    "3B": [480, 400, 330],
    "SS": [480, 400, 340],
    "OF": [500, 420, 350],
    "DH": [520, 440, 380],
    "SP": [500, 400, 320],
    "RP": [350, 280, 220],
}
