"""Historical weighted FPTS calculation for Peter Brand fantasy baseball model.

Weights recent performance more heavily while accounting for track record:
- 2026 Projection: 40% (current expectations)
- 2025 Actual: 30% (most recent performance)
- 2024 Actual: 20% (track record)
- 2023 Actual: 10% (established baseline)
"""
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.database import get_connection


# Weighting scheme for historical FPTS
YEAR_WEIGHTS = {
    2026: 0.40,  # Projection
    2025: 0.30,  # Most recent actual
    2024: 0.20,  # Prior year actual
    2023: 0.10,  # Established baseline
}


def get_historical_fpts(player_id: int) -> dict:
    """Get per-year FPTS breakdown for a player.

    Returns:
        dict with keys:
        - fpts_2023: 2023 actual FPTS
        - fpts_2024: 2024 actual FPTS
        - fpts_2025: 2025 actual FPTS
        - fpts_proj_2026: 2026 projected FPTS
        - fpts_3ya: 3-year average from player_history table
        - years_available: count of years with data
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get 2026 projection from projections table
    cursor.execute("""
        SELECT fpts FROM projections
        WHERE player_id = ? AND season = 2026 AND stat_type = 'projection'
    """, (player_id,))
    row = cursor.fetchone()
    fpts_2026 = row[0] if row else None

    # Get 2025 actual from projections table (stat_type = 'actual')
    cursor.execute("""
        SELECT fpts FROM projections
        WHERE player_id = ? AND season = 2025 AND stat_type = 'actual'
    """, (player_id,))
    row = cursor.fetchone()
    fpts_2025_proj = row[0] if row else None

    # Get historical data from player_history table
    cursor.execute("""
        SELECT fpts_2023, fpts_2024, fpts_2025, fpts_3ya
        FROM player_history
        WHERE player_id = ?
    """, (player_id,))
    row = cursor.fetchone()

    if row:
        fpts_2023 = row[0]
        fpts_2024 = row[1]
        fpts_2025_hist = row[2]
        fpts_3ya = row[3]
    else:
        fpts_2023 = None
        fpts_2024 = None
        fpts_2025_hist = None
        fpts_3ya = None

    conn.close()

    # Use player_history fpts_2025 if projection table doesn't have it
    fpts_2025 = fpts_2025_proj if fpts_2025_proj else fpts_2025_hist

    # Count years with data
    years_available = sum(1 for x in [fpts_2023, fpts_2024, fpts_2025, fpts_2026] if x is not None)

    return {
        'fpts_2023': fpts_2023,
        'fpts_2024': fpts_2024,
        'fpts_2025': fpts_2025,
        'fpts_proj_2026': fpts_2026,
        'fpts_3ya': fpts_3ya,
        'years_available': years_available,
    }


def calculate_weighted_fpts(player_id: int) -> Optional[float]:
    """Calculate historical weighted FPTS for a player.

    Uses the formula:
    weighted_fpts = (proj_2026 * 0.40) + (actual_2025 * 0.30) +
                   (actual_2024 * 0.20) + (actual_2023 * 0.10)

    For players with missing years, redistributes weights proportionally
    among available years.

    Returns:
        Weighted FPTS score, or None if no data available
    """
    history = get_historical_fpts(player_id)

    # Map years to their FPTS values
    year_fpts = {
        2026: history['fpts_proj_2026'],
        2025: history['fpts_2025'],
        2024: history['fpts_2024'],
        2023: history['fpts_2023'],
    }

    # Filter to years with data
    available = {year: fpts for year, fpts in year_fpts.items() if fpts is not None}

    if not available:
        return None

    # If we only have 2026 projection, use it directly
    if len(available) == 1 and 2026 in available:
        return available[2026]

    # Calculate adjusted weights for available years
    total_weight = sum(YEAR_WEIGHTS[year] for year in available)

    if total_weight == 0:
        return None

    # Calculate weighted average
    weighted_sum = sum(
        (YEAR_WEIGHTS[year] / total_weight) * fpts
        for year, fpts in available.items()
    )

    return round(weighted_sum, 1)


def calculate_all_weighted_fpts() -> dict:
    """Calculate weighted FPTS for all players in the database.

    Returns:
        dict mapping player_id to weighted_fpts
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get all player IDs that have projections
    cursor.execute("""
        SELECT DISTINCT player_id FROM projections
        WHERE season = 2026 AND stat_type = 'projection'
    """)

    player_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    results = {}
    for player_id in player_ids:
        weighted = calculate_weighted_fpts(player_id)
        if weighted is not None:
            results[player_id] = weighted

    return results


def get_weighted_fpts_with_breakdown(player_id: int) -> dict:
    """Get weighted FPTS along with component breakdown.

    Returns:
        dict with:
        - weighted_fpts: final weighted score
        - breakdown: dict of year -> (fpts, weight, contribution)
        - history: raw historical FPTS data
    """
    history = get_historical_fpts(player_id)
    weighted_fpts = calculate_weighted_fpts(player_id)

    year_fpts = {
        2026: history['fpts_proj_2026'],
        2025: history['fpts_2025'],
        2024: history['fpts_2024'],
        2023: history['fpts_2023'],
    }

    available = {year: fpts for year, fpts in year_fpts.items() if fpts is not None}
    total_weight = sum(YEAR_WEIGHTS[year] for year in available) if available else 1

    breakdown = {}
    for year, fpts in year_fpts.items():
        if fpts is not None:
            adjusted_weight = YEAR_WEIGHTS[year] / total_weight
            contribution = fpts * adjusted_weight
            breakdown[year] = {
                'fpts': fpts,
                'weight': round(adjusted_weight, 3),
                'contribution': round(contribution, 1),
            }
        else:
            breakdown[year] = {
                'fpts': None,
                'weight': 0,
                'contribution': 0,
            }

    return {
        'weighted_fpts': weighted_fpts,
        'breakdown': breakdown,
        'history': history,
    }


if __name__ == "__main__":
    # Test with sample data
    print("Historical FPTS Calculator")
    print("=" * 50)

    # Get all weighted FPTS
    all_weighted = calculate_all_weighted_fpts()
    print(f"\nCalculated weighted FPTS for {len(all_weighted)} players")

    if all_weighted:
        # Show top 10
        sorted_players = sorted(all_weighted.items(), key=lambda x: x[1], reverse=True)
        print("\nTop 10 by Weighted FPTS:")

        conn = get_connection()
        cursor = conn.cursor()

        for player_id, weighted in sorted_players[:10]:
            cursor.execute("SELECT name FROM players WHERE id = ?", (player_id,))
            row = cursor.fetchone()
            name = row[0] if row else f"Player {player_id}"

            breakdown = get_weighted_fpts_with_breakdown(player_id)
            years_str = []
            for year in [2026, 2025, 2024, 2023]:
                if breakdown['breakdown'][year]['fpts']:
                    years_str.append(f"{year}: {breakdown['breakdown'][year]['fpts']:.0f}")

            print(f"  {name}: {weighted:.1f} ({', '.join(years_str)})")

        conn.close()
