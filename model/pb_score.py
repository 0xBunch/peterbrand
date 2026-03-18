"""PB Score (Peter Brand Score) - Composite player valuation model.

The PB Score combines multiple factors to identify undervalued players,
inspired by the Moneyball philosophy of finding market inefficiencies.

Components and weights:
- Historical FPTS (35%): Weighted average of recent performance and projections
- League Value Gap (20%): Difference between true value and expected league price
- Positional Scarcity (15%): Premium for scarce fantasy positions
- Consistency (15%): Standard deviation of 3-year FPTS (lower = better)
- Team Context (10%): MLB team quality and lineup position
- Durability (5%): Games played track record
"""
import sys
from pathlib import Path
from typing import Optional
from statistics import stdev

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.database import get_connection
from model.historical import calculate_weighted_fpts, get_historical_fpts
from model.league_calibration import calculate_value_gap, get_position_premium
from app.config import POSITIONAL_SCARCITY, TEAM_QUALITY


# PB Score component weights
PB_WEIGHTS = {
    'historical_fpts': 0.35,
    'league_value_gap': 0.20,
    'positional_scarcity': 0.15,
    'consistency': 0.15,
    'team_context': 0.10,
    'durability': 0.05,
}


def _normalize_to_100(value: float, min_val: float, max_val: float) -> float:
    """Normalize a value to 0-100 scale."""
    if max_val == min_val:
        return 50.0
    normalized = (value - min_val) / (max_val - min_val) * 100
    return max(0, min(100, normalized))


def _calculate_historical_fpts_score(player_id: int, all_weighted: dict = None) -> float:
    """Calculate Historical FPTS component score (0-100).

    Uses weighted historical FPTS and normalizes against all players.
    """
    weighted_fpts = calculate_weighted_fpts(player_id)

    if weighted_fpts is None:
        return 0

    # Normalize: 600+ FPTS = 100, 200 FPTS = 0
    return _normalize_to_100(weighted_fpts, 200, 600)


def _calculate_league_value_gap_score(player_id: int, true_value: float = None) -> float:
    """Calculate League Value Gap component score (0-100).

    Higher score means better value (underpriced by league).
    """
    if true_value is None:
        # Estimate from weighted FPTS
        weighted = calculate_weighted_fpts(player_id)
        if weighted is None:
            return 50
        true_value = weighted * 0.06  # Rough estimate

    gap_data = calculate_value_gap(player_id, true_value)
    gap_pct = gap_data['value_gap_pct']

    # Scale: +50% gap = 100, -50% gap = 0, 0% gap = 50
    return _normalize_to_100(gap_pct, -50, 50)


def _calculate_positional_scarcity_score(positions: list) -> float:
    """Calculate Positional Scarcity component score (0-100).

    Uses predefined scarcity scores from config.
    """
    if not positions:
        return 50

    scores = []
    for pos in positions:
        pos = pos.strip().upper()
        if pos in POSITIONAL_SCARCITY:
            scores.append(POSITIONAL_SCARCITY[pos]['score'])

    return max(scores) if scores else 50


def _calculate_consistency_score(player_id: int) -> float:
    """Calculate Consistency component score (0-100).

    Based on standard deviation of available FPTS years.
    Lower std dev = higher score (more consistent).
    """
    history = get_historical_fpts(player_id)

    fpts_values = [
        v for v in [
            history['fpts_2023'],
            history['fpts_2024'],
            history['fpts_2025'],
        ] if v is not None
    ]

    if len(fpts_values) < 2:
        # Not enough data - return middle score
        return 50

    try:
        std = stdev(fpts_values)
    except Exception:
        return 50

    # Lower std dev is better
    # std of 0 = 100, std of 200 = 0
    return _normalize_to_100(200 - std, 0, 200)


def _calculate_team_context_score(team: str, position: str = None) -> float:
    """Calculate Team Context component score (0-100).

    Based on MLB team quality (contender vs rebuilder).
    """
    if not team:
        return 50

    team = team.upper().strip()
    quality = TEAM_QUALITY.get(team, 50)

    return float(quality)


def _calculate_durability_score(player_id: int) -> float:
    """Calculate Durability component score (0-100).

    Based on games played in recent years.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get games data from player_history
    cursor.execute("""
        SELECT games_2023, games_2024, games_2025
        FROM player_history
        WHERE player_id = ?
    """, (player_id,))

    row = cursor.fetchone()

    if not row:
        # Try to get from projections/stats
        cursor.execute("""
            SELECT
                MAX(CASE WHEN season = 2025 THEN COALESCE(gs, app) END) as g25,
                MAX(CASE WHEN season = 2024 THEN COALESCE(gs, app) END) as g24,
                MAX(CASE WHEN season = 2023 THEN COALESCE(gs, app) END) as g23
            FROM projections
            WHERE player_id = ? AND stat_type = 'actual'
        """, (player_id,))
        row = cursor.fetchone()

    conn.close()

    if not row or all(v is None for v in row):
        return 35  # Unknown - default to below average

    games = [g for g in row if g is not None]

    if not games:
        return 35

    # Average games across available years
    avg_games = sum(games) / len(games)

    # Check if pitcher (typically fewer games)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT positions FROM players WHERE id = ?", (player_id,))
    pos_row = cursor.fetchone()
    conn.close()

    positions = pos_row[0] if pos_row else ''
    is_pitcher = 'SP' in positions or 'RP' in positions

    if is_pitcher:
        # Pitchers: 30+ GS = 100, 15 GS = 50, 5 GS = 0
        return _normalize_to_100(avg_games, 5, 30)
    else:
        # Hitters: 150+ G = 100, 100 G = 50, 50 G = 0
        return _normalize_to_100(avg_games, 50, 150)


def calculate_pb_score(player_id: int) -> dict:
    """Calculate PB Score for a single player.

    Returns:
        dict with:
        - pb_score: Final weighted score (0-100)
        - components: Individual component scores
        - true_value: Estimated auction value
        - league_price: Expected league price
        - value_gap: Difference (positive = undervalued)
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get player info
    cursor.execute("""
        SELECT p.name, p.mlb_team, p.positions, p.primary_position, proj.fpts
        FROM players p
        LEFT JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        WHERE p.id = ?
    """, (player_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    name = row[0]
    team = row[1] or ''
    positions_str = row[2] or ''
    primary_pos = row[3] or (positions_str.split(',')[0] if positions_str else 'DH')
    fpts_proj = row[4] or 0

    positions = [p.strip() for p in positions_str.split(',') if p.strip()]

    # Calculate weighted FPTS for true value estimation
    weighted_fpts = calculate_weighted_fpts(player_id) or fpts_proj
    true_value = weighted_fpts * 0.055  # ~$0.055 per weighted FPTS

    # Calculate all components
    components = {
        'historical_fpts': _calculate_historical_fpts_score(player_id),
        'league_value_gap': _calculate_league_value_gap_score(player_id, true_value),
        'positional_scarcity': _calculate_positional_scarcity_score(positions),
        'consistency': _calculate_consistency_score(player_id),
        'team_context': _calculate_team_context_score(team, primary_pos),
        'durability': _calculate_durability_score(player_id),
    }

    # Calculate weighted PB Score
    pb_score = sum(
        components[k] * PB_WEIGHTS[k]
        for k in components
    )

    # Get league price expectation
    gap_data = calculate_value_gap(player_id, true_value)

    return {
        'player_id': player_id,
        'name': name,
        'team': team,
        'position': primary_pos,
        'pb_score': round(pb_score, 1),
        'components': {k: round(v, 1) for k, v in components.items()},
        'true_value': round(true_value, 1),
        'league_price': gap_data['expected_league_price'],
        'value_gap': gap_data['value_gap'],
        'weighted_fpts': round(weighted_fpts, 1) if weighted_fpts else None,
    }


def calculate_all_pb_scores() -> int:
    """Batch calculate and store PB Scores for all players.

    Updates the pb_scores table with component scores and computed values.

    Returns:
        Number of players processed
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get all players with 2026 projections
    cursor.execute("""
        SELECT DISTINCT p.id
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
        WHERE proj.season = 2026 AND proj.stat_type = 'projection'
            AND proj.fpts IS NOT NULL
    """)

    player_ids = [row[0] for row in cursor.fetchall()]

    processed = 0

    for player_id in player_ids:
        result = calculate_pb_score(player_id)

        if result is None:
            continue

        # Store in pb_scores table
        cursor.execute("""
            INSERT OR REPLACE INTO pb_scores (
                player_id,
                historical_fpts,
                league_value_gap,
                positional_scarcity,
                consistency,
                team_context,
                durability,
                pb_score,
                true_value,
                league_price,
                value_gap
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            player_id,
            result['components']['historical_fpts'],
            result['components']['league_value_gap'],
            result['components']['positional_scarcity'],
            result['components']['consistency'],
            result['components']['team_context'],
            result['components']['durability'],
            result['pb_score'],
            result['true_value'],
            result['league_price'],
            result['value_gap'],
        ))

        processed += 1

    conn.commit()
    conn.close()

    return processed


def get_top_pb_scores(limit: int = 50, position: str = None) -> list:
    """Get players with highest PB Scores.

    Args:
        limit: Maximum number of players to return
        position: Optional position filter

    Returns:
        list of player dicts with PB Score data
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            p.id, p.name, p.mlb_team, p.positions, p.primary_position,
            proj.fpts,
            pb.pb_score, pb.true_value, pb.league_price, pb.value_gap,
            pb.historical_fpts, pb.league_value_gap, pb.positional_scarcity,
            pb.consistency, pb.team_context, pb.durability
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        JOIN pb_scores pb ON p.id = pb.player_id
        WHERE pb.pb_score IS NOT NULL
    """

    params = []
    if position:
        query += " AND p.positions LIKE ?"
        params.append(f'%{position}%')

    query += " ORDER BY pb.pb_score DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        results.append({
            'player_id': row[0],
            'name': row[1],
            'team': row[2],
            'positions': row[3],
            'primary_position': row[4],
            'fpts_proj': row[5],
            'pb_score': row[6],
            'true_value': row[7],
            'league_price': row[8],
            'value_gap': row[9],
            'components': {
                'historical_fpts': row[10],
                'league_value_gap': row[11],
                'positional_scarcity': row[12],
                'consistency': row[13],
                'team_context': row[14],
                'durability': row[15],
            }
        })

    return results


def get_undervalued_players(min_gap: float = 5.0, limit: int = 25) -> list:
    """Find players where true value exceeds expected league price.

    Args:
        min_gap: Minimum dollar gap to include
        limit: Maximum results

    Returns:
        list of undervalued players sorted by gap
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.id, p.name, p.mlb_team, p.primary_position,
            proj.fpts,
            pb.pb_score, pb.true_value, pb.league_price, pb.value_gap
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        JOIN pb_scores pb ON p.id = pb.player_id
        WHERE pb.value_gap >= ?
        ORDER BY pb.value_gap DESC
        LIMIT ?
    """, (min_gap, limit))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            'player_id': row[0],
            'name': row[1],
            'team': row[2],
            'position': row[3],
            'fpts': row[4],
            'pb_score': row[5],
            'true_value': row[6],
            'league_price': row[7],
            'value_gap': row[8],
        }
        for row in rows
    ]


def get_pb_score_summary() -> dict:
    """Get summary statistics for PB Scores.

    Returns:
        dict with score distribution and value gap analysis
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Overall stats
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            AVG(pb_score) as avg_score,
            MIN(pb_score) as min_score,
            MAX(pb_score) as max_score,
            AVG(value_gap) as avg_gap,
            SUM(CASE WHEN value_gap > 0 THEN 1 ELSE 0 END) as undervalued,
            SUM(CASE WHEN value_gap < 0 THEN 1 ELSE 0 END) as overvalued
        FROM pb_scores
        WHERE pb_score IS NOT NULL
    """)

    row = cursor.fetchone()

    # By position
    cursor.execute("""
        SELECT
            p.primary_position,
            COUNT(*) as count,
            AVG(pb.pb_score) as avg_score,
            AVG(pb.value_gap) as avg_gap
        FROM pb_scores pb
        JOIN players p ON pb.player_id = p.id
        WHERE pb.pb_score IS NOT NULL AND p.primary_position IS NOT NULL
        GROUP BY p.primary_position
        ORDER BY avg_score DESC
    """)

    position_rows = cursor.fetchall()
    conn.close()

    return {
        'total_players': row[0],
        'avg_score': round(row[1], 1) if row[1] else 0,
        'min_score': round(row[2], 1) if row[2] else 0,
        'max_score': round(row[3], 1) if row[3] else 0,
        'avg_value_gap': round(row[4], 1) if row[4] else 0,
        'undervalued_count': row[5] or 0,
        'overvalued_count': row[6] or 0,
        'by_position': {
            pos_row[0]: {
                'count': pos_row[1],
                'avg_score': round(pos_row[2], 1),
                'avg_gap': round(pos_row[3], 1),
            }
            for pos_row in position_rows
        }
    }


def calculate_tier(fpts: float, position: str) -> int:
    """Determine tier based on FPTS and position-specific cutoffs."""
    from app.config import TIER_CUTOFFS

    cutoffs = TIER_CUTOFFS.get(position, [400, 300, 200])

    if fpts >= cutoffs[0]:
        return 1
    elif fpts >= cutoffs[1]:
        return 2
    elif fpts >= cutoffs[2]:
        return 3
    else:
        return 4


def calculate_bid_range(true_value: float, position: str, remaining_budget: int = 254) -> dict:
    """Calculate bid floor, target, ceiling, and max for a player.

    Returns dict with floor, target, ceiling, max_bid
    """
    from app.config import BUDGET_STRATEGY

    # Position-based multipliers
    pos_mult = {
        'C': 0.6, '1B': 0.9, '2B': 1.0, '3B': 1.1,
        'SS': 1.0, 'OF': 1.0, 'DH': 0.7, 'SP': 1.0, 'RP': 0.8
    }
    mult = pos_mult.get(position, 1.0)

    # Base target from true value
    target = max(1, round(true_value * mult))

    # Bid range
    floor = max(1, int(target * 0.7))
    ceiling = int(target * 1.3)

    # MAX bid calculation
    pos_budget = BUDGET_STRATEGY.get(position, {}).get('max', 50)
    max_bid = min(
        int(ceiling * 1.25),          # 25% above ceiling
        int(remaining_budget * 0.4),  # Never >40% of remaining
        pos_budget                    # Stay within position budget
    )
    max_bid = max(max_bid, target)  # Max should be at least target

    return {
        'floor': floor,
        'target': target,
        'ceiling': ceiling,
        'max_bid': max_bid,
    }


def generate_all_tiers_and_bids():
    """Generate tier assignments and bid ranges for all players.

    Consolidates tier/bid generation with PB Score for single execution.
    """
    conn = get_connection()
    cursor = conn.cursor()

    positions = ['C', '1B', '2B', '3B', 'SS', 'OF', 'DH', 'SP', 'RP']
    tier_counts = {pos: {1: 0, 2: 0, 3: 0, 4: 0} for pos in positions}

    # Get all players with projections and PB scores
    cursor.execute("""
        SELECT
            p.id, p.name, p.positions, p.primary_position,
            proj.fpts,
            pb.pb_score, pb.true_value, pb.league_price, pb.value_gap
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        LEFT JOIN pb_scores pb ON p.id = pb.player_id
        WHERE proj.fpts IS NOT NULL
        ORDER BY proj.fpts DESC
    """)

    players = cursor.fetchall()

    for player in players:
        player_id = player[0]
        positions_str = player[2] or 'DH'
        primary_pos = player[3] or positions_str.split(',')[0].strip()
        fpts = player[4] or 0
        true_value = player[6] or (fpts * 0.055)  # Fallback estimate

        # Get all positions this player is eligible for
        player_positions = [p.strip() for p in positions_str.split(',') if p.strip()]
        if not player_positions:
            player_positions = [primary_pos]

        # Calculate tier and bids for each eligible position
        for pos in player_positions:
            tier = calculate_tier(fpts, pos)
            tier_counts.get(pos, {1: 0, 2: 0, 3: 0, 4: 0})[tier] = tier_counts.get(pos, {1: 0, 2: 0, 3: 0, 4: 0}).get(tier, 0) + 1

            bids = calculate_bid_range(true_value, pos)

            cursor.execute("""
                INSERT OR REPLACE INTO position_tiers
                (player_id, position, tier, rank_in_tier, bid_floor, bid_target, bid_ceiling, max_bid)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                player_id, pos, tier,
                tier_counts.get(pos, {}).get(tier, 0),
                bids['floor'], bids['target'], bids['ceiling'], bids['max_bid']
            ))

    conn.commit()
    conn.close()

    print("\nTier Generation Complete:")
    for pos in positions:
        counts = tier_counts.get(pos, {})
        print(f"  {pos}: T1={counts.get(1, 0)}, T2={counts.get(2, 0)}, T3={counts.get(3, 0)}, T4={counts.get(4, 0)}")

    return tier_counts


if __name__ == "__main__":
    print("PB Score Calculator (Peter Brand Score)")
    print("=" * 60)

    # Calculate all scores
    print("\nCalculating PB Scores for all players...")
    count = calculate_all_pb_scores()
    print(f"Processed {count} players")

    # Show summary
    print("\nScore Summary:")
    summary = get_pb_score_summary()
    print(f"  Total Players: {summary['total_players']}")
    print(f"  Average Score: {summary['avg_score']}")
    print(f"  Score Range: {summary['min_score']} - {summary['max_score']}")
    print(f"  Avg Value Gap: ${summary['avg_value_gap']}")
    print(f"  Undervalued: {summary['undervalued_count']} | Overvalued: {summary['overvalued_count']}")

    # By position
    print("\nBy Position:")
    for pos, data in summary['by_position'].items():
        print(f"  {pos}: {data['count']} players, avg score {data['avg_score']}, avg gap ${data['avg_gap']}")

    # Top overall
    print("\nTop 15 PB Scores:")
    top = get_top_pb_scores(limit=15)
    for i, p in enumerate(top, 1):
        gap_str = f"+${p['value_gap']:.0f}" if p['value_gap'] > 0 else f"-${abs(p['value_gap']):.0f}"
        print(f"  {i:2}. {p['name']} ({p['primary_position']}, {p['team']}): "
              f"{p['pb_score']:.1f} | ${p['true_value']:.0f} true vs ${p['league_price']:.0f} league ({gap_str})")

    # Best value opportunities
    print("\nTop Value Opportunities (largest positive gaps):")
    undervalued = get_undervalued_players(min_gap=3.0, limit=10)
    for p in undervalued:
        print(f"  {p['name']} ({p['position']}): "
              f"${p['true_value']:.0f} true vs ${p['league_price']:.0f} expected "
              f"(+${p['value_gap']:.0f} edge)")

    # Generate tiers and bid ranges
    print("\n" + "=" * 60)
    print("Generating Position Tiers and Bid Ranges...")
    generate_all_tiers_and_bids()
