"""BATCAVE - Real-time Inflation and Value Adjustment Engine

This module calculates inflation/deflation as the draft progresses and
adjusts player values in real-time based on remaining budget pool and
player value remaining.
"""

from typing import Optional
from data.database import get_connection


def get_draft_state() -> dict:
    """Get current draft state for inflation calculation.

    Returns:
        dict with:
        - total_budget: Total budget across all teams
        - total_spent: Total spent so far
        - budget_remaining: Remaining budget pool
        - players_drafted: Count of players drafted
        - players_remaining: Count of undrafted players with value
        - value_remaining: Sum of auction values for undrafted players
        - value_drafted: Sum of expected values for drafted players
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get total budget across all teams
    cursor.execute("""
        SELECT COALESCE(SUM(budget_remaining), 0), COUNT(*)
        FROM league_teams
    """)
    row = cursor.fetchone()
    budget_remaining = row[0] or 0
    num_teams = row[1] or 12

    # Estimate total budget (320 per team typical)
    total_budget = num_teams * 320

    # Get total spent
    cursor.execute("SELECT COALESCE(SUM(salary), 0), COUNT(*) FROM draft_picks")
    row = cursor.fetchone()
    total_spent = row[0] or 0
    players_drafted = row[1] or 0

    # Get sum of expected values for drafted players
    cursor.execute("""
        SELECT COALESCE(SUM(ab.auction_value), 0)
        FROM draft_picks dp
        JOIN ab_scores ab ON dp.player_id = ab.player_id
    """)
    value_drafted = cursor.fetchone()[0] or 0

    # Get undrafted player value sum
    cursor.execute("""
        SELECT COALESCE(SUM(ab.auction_value), 0), COUNT(*)
        FROM players p
        JOIN ab_scores ab ON p.id = ab.player_id
        LEFT JOIN draft_picks dp ON p.id = dp.player_id
        WHERE dp.id IS NULL AND ab.auction_value > 0
    """)
    row = cursor.fetchone()
    value_remaining = row[0] or 0
    players_remaining = row[1] or 0

    conn.close()

    return {
        'total_budget': total_budget,
        'total_spent': total_spent,
        'budget_remaining': total_budget - total_spent,
        'players_drafted': players_drafted,
        'players_remaining': players_remaining,
        'value_remaining': value_remaining,
        'value_drafted': value_drafted,
    }


def calculate_inflation(draft_state: Optional[dict] = None) -> float:
    """Calculate current inflation/deflation rate.

    Inflation occurs when remaining budget exceeds remaining player value,
    meaning prices will go up. Deflation is the opposite.

    Args:
        draft_state: Optional pre-computed draft state dict

    Returns:
        Inflation rate as decimal (e.g., 0.15 = 15% inflation)
        Positive = inflation (prices rising)
        Negative = deflation (prices falling)
    """
    if draft_state is None:
        draft_state = get_draft_state()

    budget_remaining = draft_state['budget_remaining']
    value_remaining = draft_state['value_remaining']

    # Avoid division by zero
    if value_remaining <= 0:
        return 0.0

    # Inflation = (Budget Remaining / Value Remaining) - 1
    # If budget > value, inflation is positive (prices rising)
    # If budget < value, inflation is negative (prices falling)
    inflation = (budget_remaining / value_remaining) - 1

    return inflation


def apply_inflation(base_value: float, inflation: float) -> float:
    """Adjust a player's value for current inflation.

    Args:
        base_value: Original auction value
        inflation: Inflation rate (from calculate_inflation)

    Returns:
        Adjusted value accounting for inflation
    """
    return base_value * (1 + inflation)


def get_adjusted_bid_range(player_id: int, inflation: Optional[float] = None) -> dict:
    """Get inflation-adjusted bid range for a player.

    Args:
        player_id: Player database ID
        inflation: Optional pre-computed inflation rate

    Returns:
        dict with floor, target, ceiling (all adjusted for inflation)
    """
    if inflation is None:
        inflation = calculate_inflation()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COALESCE(pt.bid_floor, 1) as bid_floor,
            COALESCE(pt.bid_target, 1) as bid_target,
            COALESCE(pt.bid_ceiling, 1) as bid_ceiling,
            COALESCE(ab.auction_value, 1) as auction_value
        FROM players p
        LEFT JOIN position_tiers pt ON p.id = pt.player_id
            AND pt.position = p.primary_position
        LEFT JOIN ab_scores ab ON p.id = ab.player_id
        WHERE p.id = ?
    """, (player_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return {'floor': 1, 'target': 1, 'ceiling': 1, 'inflation': inflation}

    bid_floor, bid_target, bid_ceiling, auction_value = row

    # Apply inflation adjustment
    adj_floor = max(1, int(apply_inflation(bid_floor, inflation)))
    adj_target = max(1, int(apply_inflation(bid_target, inflation)))
    adj_ceiling = max(1, int(apply_inflation(bid_ceiling, inflation)))
    adj_value = max(1, int(apply_inflation(auction_value, inflation)))

    return {
        'floor': adj_floor,
        'target': adj_target,
        'ceiling': adj_ceiling,
        'adjusted_value': adj_value,
        'base_value': auction_value,
        'inflation': inflation,
    }


def recalculate_all_adjusted_values() -> int:
    """Recalculate all player values with current inflation.

    This updates the bid ranges in position_tiers to reflect
    current market conditions.

    Returns:
        Number of players updated
    """
    inflation = calculate_inflation()

    conn = get_connection()
    cursor = conn.cursor()

    # Get all undrafted players with bid ranges
    cursor.execute("""
        SELECT pt.player_id, pt.position, pt.bid_floor, pt.bid_target, pt.bid_ceiling
        FROM position_tiers pt
        LEFT JOIN draft_picks dp ON pt.player_id = dp.player_id
        WHERE dp.id IS NULL
    """)

    rows = cursor.fetchall()
    count = 0

    for row in rows:
        player_id, position, floor, target, ceiling = row

        # Apply inflation
        adj_floor = max(1, int(apply_inflation(floor, inflation)))
        adj_target = max(1, int(apply_inflation(target, inflation)))
        adj_ceiling = max(1, int(apply_inflation(ceiling, inflation)))

        cursor.execute("""
            UPDATE position_tiers
            SET bid_floor = ?, bid_target = ?, bid_ceiling = ?
            WHERE player_id = ? AND position = ?
        """, (adj_floor, adj_target, adj_ceiling, player_id, position))

        count += 1

    conn.commit()
    conn.close()

    return count


def get_inflation_summary() -> dict:
    """Get a summary of current market conditions.

    Returns:
        dict with market state summary for display
    """
    state = get_draft_state()
    inflation = calculate_inflation(state)

    # Determine market condition
    if inflation > 0.15:
        condition = "HOT"
        description = "Heavy inflation - be patient, prices elevated"
    elif inflation > 0.05:
        condition = "WARM"
        description = "Mild inflation - target values slightly high"
    elif inflation < -0.15:
        condition = "COLD"
        description = "Heavy deflation - bargains available"
    elif inflation < -0.05:
        condition = "COOL"
        description = "Mild deflation - slight value available"
    else:
        condition = "NEUTRAL"
        description = "Market balanced - values accurate"

    return {
        'inflation': inflation,
        'inflation_pct': f"{inflation * 100:+.1f}%",
        'condition': condition,
        'description': description,
        'budget_remaining': state['budget_remaining'],
        'value_remaining': state['value_remaining'],
        'players_drafted': state['players_drafted'],
        'players_remaining': state['players_remaining'],
    }
