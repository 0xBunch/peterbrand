"""League calibration module - analyze draft history to find value gaps.

Analyzes historical draft data from Dedeaux Field 4.0 to understand:
- Average $/FPTS by position and tier
- Which positions the league systematically overpays/underpays for
- Value gaps between model valuation and expected league price
"""
import sys
from pathlib import Path
from typing import Optional
from statistics import mean, stdev

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.database import get_connection
from app.config import POSITIONAL_SCARCITY, TIER_CUTOFFS


def calculate_league_prices() -> dict:
    """Analyze draft_history table to calculate average $/FPTS by position.

    Computes:
    - Average salary by position and tier
    - Average FPTS by position and tier
    - Dollars per FPTS ratio
    - Sample size for confidence

    Results are stored in league_prices table.

    Returns:
        dict mapping (position, tier) to price data
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get all draft history with FPTS data
    cursor.execute("""
        SELECT
            dh.position,
            dh.salary,
            dh.fpts_total,
            dh.season
        FROM draft_history dh
        WHERE dh.salary > 0
            AND dh.fpts_total IS NOT NULL
            AND dh.fpts_total > 0
            AND dh.position IS NOT NULL
    """)

    rows = cursor.fetchall()

    if not rows:
        print("No draft history data found. Using default pricing.")
        conn.close()
        return _get_default_league_prices()

    # Organize by position
    position_data = {}
    for row in rows:
        position = _normalize_position(row[0])
        if position is None:
            continue

        salary = row[1]
        fpts = row[2]

        if position not in position_data:
            position_data[position] = []

        position_data[position].append({
            'salary': salary,
            'fpts': fpts,
            'dollars_per_fpts': salary / fpts if fpts > 0 else 0,
        })

    # Calculate tier-based pricing
    results = {}

    for position, data_points in position_data.items():
        cutoffs = TIER_CUTOFFS.get(position, [400, 300, 200])

        # Group by tier
        tier_data = {1: [], 2: [], 3: [], 4: []}

        for dp in data_points:
            tier = _get_tier_for_fpts(dp['fpts'], cutoffs)
            tier_data[tier].append(dp)

        # Calculate averages per tier
        for tier, tier_points in tier_data.items():
            if not tier_points:
                # Use extrapolated defaults if no data
                avg_salary = _estimate_tier_salary(position, tier)
                avg_fpts = _estimate_tier_fpts(position, tier)
                sample_size = 0
            else:
                avg_salary = mean(dp['salary'] for dp in tier_points)
                avg_fpts = mean(dp['fpts'] for dp in tier_points)
                sample_size = len(tier_points)

            dollars_per_fpts = avg_salary / avg_fpts if avg_fpts > 0 else 0.1

            results[(position, tier)] = {
                'position': position,
                'tier': tier,
                'avg_salary': round(avg_salary, 1),
                'avg_fpts': round(avg_fpts, 1),
                'dollars_per_fpts': round(dollars_per_fpts, 4),
                'sample_size': sample_size,
            }

            # Store in database
            cursor.execute("""
                INSERT OR REPLACE INTO league_prices
                (position, tier, avg_salary, avg_fpts, dollars_per_fpts, sample_size)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (position, tier, avg_salary, avg_fpts, dollars_per_fpts, sample_size))

    conn.commit()
    conn.close()

    return results


def _normalize_position(pos: str) -> Optional[str]:
    """Normalize position string to standard format."""
    if not pos:
        return None

    pos = pos.upper().strip()

    # Handle multi-position - take primary
    if ',' in pos:
        pos = pos.split(',')[0].strip()

    # Map common variations
    position_map = {
        'C': 'C',
        'CATCHER': 'C',
        '1B': '1B',
        'FIRST': '1B',
        '2B': '2B',
        'SECOND': '2B',
        '3B': '3B',
        'THIRD': '3B',
        'SS': 'SS',
        'SHORT': 'SS',
        'SHORTSTOP': 'SS',
        'OF': 'OF',
        'LF': 'OF',
        'CF': 'OF',
        'RF': 'OF',
        'OUTFIELD': 'OF',
        'DH': 'DH',
        'SP': 'SP',
        'STARTER': 'SP',
        'RP': 'RP',
        'RELIEVER': 'RP',
        'CL': 'RP',
        'CLOSER': 'RP',
        'P': 'SP',  # Default pitcher to SP
    }

    return position_map.get(pos)


def _get_tier_for_fpts(fpts: float, cutoffs: list) -> int:
    """Determine tier based on FPTS."""
    if fpts >= cutoffs[0]:
        return 1
    elif fpts >= cutoffs[1]:
        return 2
    elif fpts >= cutoffs[2]:
        return 3
    else:
        return 4


def _estimate_tier_salary(position: str, tier: int) -> float:
    """Estimate typical salary for position/tier when no data available."""
    # Base estimates from fantasy baseball conventions
    base_salaries = {
        1: {'C': 20, '1B': 35, '2B': 30, '3B': 35, 'SS': 35, 'OF': 40, 'DH': 25, 'SP': 35, 'RP': 20},
        2: {'C': 10, '1B': 18, '2B': 15, '3B': 20, 'SS': 18, 'OF': 20, 'DH': 12, 'SP': 18, 'RP': 10},
        3: {'C': 4, '1B': 8, '2B': 6, '3B': 8, 'SS': 7, 'OF': 8, 'DH': 5, 'SP': 8, 'RP': 4},
        4: {'C': 1, '1B': 2, '2B': 2, '3B': 2, 'SS': 2, 'OF': 2, 'DH': 1, 'SP': 2, 'RP': 1},
    }
    return base_salaries.get(tier, {}).get(position, 5)


def _estimate_tier_fpts(position: str, tier: int) -> float:
    """Estimate typical FPTS for position/tier when no data available."""
    cutoffs = TIER_CUTOFFS.get(position, [400, 300, 200])

    # Use midpoint of tier range
    if tier == 1:
        return cutoffs[0] + 50  # Above tier 1 cutoff
    elif tier == 2:
        return (cutoffs[0] + cutoffs[1]) / 2
    elif tier == 3:
        return (cutoffs[1] + cutoffs[2]) / 2
    else:
        return cutoffs[2] - 50  # Below tier 3 cutoff


def _get_default_league_prices() -> dict:
    """Return default league prices when no history available."""
    results = {}
    positions = ['C', '1B', '2B', '3B', 'SS', 'OF', 'DH', 'SP', 'RP']

    for position in positions:
        for tier in [1, 2, 3, 4]:
            avg_salary = _estimate_tier_salary(position, tier)
            avg_fpts = _estimate_tier_fpts(position, tier)
            dollars_per_fpts = avg_salary / avg_fpts if avg_fpts > 0 else 0.1

            results[(position, tier)] = {
                'position': position,
                'tier': tier,
                'avg_salary': avg_salary,
                'avg_fpts': avg_fpts,
                'dollars_per_fpts': round(dollars_per_fpts, 4),
                'sample_size': 0,
            }

    return results


def get_position_premium(position: str) -> float:
    """Return multiplier showing if league overpays/underpays for position.

    A value > 1.0 means the league overpays for this position.
    A value < 1.0 means the league underpays (value opportunity).

    The premium is calculated by comparing position $/FPTS to league average.

    Returns:
        float multiplier (e.g., 1.15 means 15% overpaid)
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get all league prices
    cursor.execute("""
        SELECT position, tier, dollars_per_fpts, sample_size
        FROM league_prices
        WHERE sample_size > 0
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        # Fall back to scarcity-based estimate
        scarcity = POSITIONAL_SCARCITY.get(position, {}).get('score', 50)
        # High scarcity positions tend to be overpaid
        return 0.8 + (scarcity / 100) * 0.4  # Range: 0.8 to 1.2

    # Calculate league average $/FPTS (weighted by sample size)
    total_weight = sum(row[3] for row in rows)
    if total_weight == 0:
        return 1.0

    league_avg_dpf = sum(row[2] * row[3] for row in rows) / total_weight

    # Calculate position average $/FPTS
    position_rows = [row for row in rows if row[0] == position]
    if not position_rows:
        return 1.0

    pos_weight = sum(row[3] for row in position_rows)
    if pos_weight == 0:
        return 1.0

    position_avg_dpf = sum(row[2] * row[3] for row in position_rows) / pos_weight

    # Premium is ratio of position to league average
    if league_avg_dpf == 0:
        return 1.0

    premium = position_avg_dpf / league_avg_dpf

    # Clamp to reasonable range
    return max(0.5, min(2.0, round(premium, 3)))


def calculate_value_gap(player_id: int, true_value: float) -> dict:
    """Compare model value to expected league price.

    Args:
        player_id: Player database ID
        true_value: Model's estimated true dollar value

    Returns:
        dict with:
        - expected_league_price: What league typically pays
        - value_gap: true_value - expected_league_price (positive = undervalued)
        - value_gap_pct: Percentage difference
        - recommendation: "buy", "sell", or "fair"
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get player position and projected FPTS
    cursor.execute("""
        SELECT p.primary_position, p.positions, proj.fpts
        FROM players p
        LEFT JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        WHERE p.id = ?
    """, (player_id,))

    row = cursor.fetchone()
    if not row:
        conn.close()
        return {
            'expected_league_price': true_value,
            'value_gap': 0,
            'value_gap_pct': 0,
            'recommendation': 'fair',
        }

    position = row[0] or (row[1].split(',')[0] if row[1] else 'DH')
    fpts = row[2] or 0

    # Determine tier
    cutoffs = TIER_CUTOFFS.get(position, [400, 300, 200])
    tier = _get_tier_for_fpts(fpts, cutoffs)

    # Get league price for this position/tier
    cursor.execute("""
        SELECT avg_salary, dollars_per_fpts, sample_size
        FROM league_prices
        WHERE position = ? AND tier = ?
    """, (position, tier))

    price_row = cursor.fetchone()
    conn.close()

    if price_row and price_row[2] > 0:
        # Use historical data
        expected_price = price_row[0]
        # Also adjust based on FPTS relative to tier average
        tier_fpts = _estimate_tier_fpts(position, tier)
        fpts_adjustment = fpts / tier_fpts if tier_fpts > 0 else 1.0
        expected_price = expected_price * fpts_adjustment
    else:
        # Use estimated price
        expected_price = _estimate_tier_salary(position, tier)
        # Adjust for position premium
        premium = get_position_premium(position)
        expected_price = expected_price * premium

    expected_price = round(expected_price, 1)

    # Calculate gap
    value_gap = true_value - expected_price
    value_gap_pct = (value_gap / expected_price * 100) if expected_price > 0 else 0

    # Determine recommendation
    if value_gap_pct > 15:
        recommendation = 'buy'  # Undervalued by league
    elif value_gap_pct < -15:
        recommendation = 'sell'  # Overvalued by league
    else:
        recommendation = 'fair'

    return {
        'expected_league_price': expected_price,
        'value_gap': round(value_gap, 1),
        'value_gap_pct': round(value_gap_pct, 1),
        'recommendation': recommendation,
    }


def get_all_position_premiums() -> dict:
    """Get premiums for all positions.

    Returns:
        dict mapping position to premium multiplier
    """
    positions = ['C', '1B', '2B', '3B', 'SS', 'OF', 'DH', 'SP', 'RP']
    return {pos: get_position_premium(pos) for pos in positions}


def find_league_value_opportunities(min_gap_pct: float = 20.0) -> list:
    """Find players where model value differs significantly from league pricing.

    Args:
        min_gap_pct: Minimum percentage gap to flag

    Returns:
        list of players with significant value gaps
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get all players with projections and scores
    cursor.execute("""
        SELECT
            p.id, p.name, p.primary_position,
            proj.fpts,
            pb.true_value
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        LEFT JOIN pb_scores pb ON p.id = pb.player_id
        WHERE proj.fpts IS NOT NULL
        ORDER BY proj.fpts DESC
    """)

    players = cursor.fetchall()
    conn.close()

    opportunities = []

    for player in players:
        player_id = player[0]
        name = player[1]
        position = player[2]
        fpts = player[3]
        true_value = player[4]

        if true_value is None:
            # Estimate true value from FPTS if not calculated
            true_value = fpts * 0.06  # Rough estimate: ~$0.06 per FPTS

        gap_data = calculate_value_gap(player_id, true_value)

        if abs(gap_data['value_gap_pct']) >= min_gap_pct:
            opportunities.append({
                'player_id': player_id,
                'name': name,
                'position': position,
                'fpts': fpts,
                'true_value': true_value,
                'expected_price': gap_data['expected_league_price'],
                'value_gap': gap_data['value_gap'],
                'value_gap_pct': gap_data['value_gap_pct'],
                'recommendation': gap_data['recommendation'],
            })

    # Sort by absolute gap percentage
    opportunities.sort(key=lambda x: abs(x['value_gap_pct']), reverse=True)

    return opportunities


if __name__ == "__main__":
    print("League Calibration Module")
    print("=" * 50)

    # Calculate and store league prices
    print("\nCalculating league prices from draft history...")
    prices = calculate_league_prices()
    print(f"Calculated prices for {len(prices)} position/tier combinations")

    # Show position premiums
    print("\nPosition Premiums (>1.0 = overpaid, <1.0 = undervalued):")
    premiums = get_all_position_premiums()
    for pos, premium in sorted(premiums.items(), key=lambda x: x[1], reverse=True):
        status = "OVERPAID" if premium > 1.1 else "UNDERVALUED" if premium < 0.9 else "fair"
        print(f"  {pos}: {premium:.3f} ({status})")

    # Find value opportunities
    print("\nTop Value Opportunities (gap >= 20%):")
    opportunities = find_league_value_opportunities(min_gap_pct=20.0)
    for opp in opportunities[:10]:
        direction = "BUY" if opp['recommendation'] == 'buy' else "SELL"
        print(f"  {opp['name']} ({opp['position']}): "
              f"${opp['true_value']:.0f} true vs ${opp['expected_price']:.0f} league "
              f"({opp['value_gap_pct']:+.1f}%) - {direction}")
