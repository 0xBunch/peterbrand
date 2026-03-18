"""Player Insights - Trajectory, consistency, and breakout detection.

Analyzes player trends over multiple years to identify rising stars,
declining assets, and consistent performers.
"""
import sys
from pathlib import Path
from statistics import stdev, mean

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.database import get_connection
from model.historical import get_historical_fpts


# Trajectory classifications
TRAJECTORY_RISING = 'RISING'
TRAJECTORY_DECLINING = 'DECLINING'
TRAJECTORY_BREAKOUT = 'BREAKOUT_CANDIDATE'
TRAJECTORY_STEADY = 'STEADY'
TRAJECTORY_BOUNCE = 'BOUNCEBACK'
TRAJECTORY_UNKNOWN = 'UNKNOWN'


def detect_trajectory(player_id: int) -> dict:
    """Classify player's trajectory based on historical FPTS.

    Returns:
        Dict with trajectory type and supporting data
    """
    history = get_historical_fpts(player_id)

    fpts_2023 = history.get('fpts_2023')
    fpts_2024 = history.get('fpts_2024')
    fpts_2025 = history.get('fpts_2025')
    fpts_proj = history.get('fpts_proj')

    # Need at least projection and one year
    if fpts_proj is None:
        return {'trajectory': TRAJECTORY_UNKNOWN, 'confidence': 0}

    years = [y for y in [fpts_2023, fpts_2024, fpts_2025] if y is not None]

    if not years:
        return {
            'trajectory': TRAJECTORY_UNKNOWN,
            'confidence': 20,
            'reason': 'No historical data'
        }

    avg_historical = mean(years) if years else 0

    # Breakout: Projection significantly higher than historical
    if fpts_proj > avg_historical * 1.15 and fpts_proj > 350:
        return {
            'trajectory': TRAJECTORY_BREAKOUT,
            'confidence': 75,
            'reason': f'Projected {fpts_proj:.0f} vs historical avg {avg_historical:.0f}',
            'delta': fpts_proj - avg_historical
        }

    # Rising: Consistent year-over-year improvement
    if len(years) >= 2:
        if fpts_2025 and fpts_2024:
            if fpts_2025 > fpts_2024 * 1.05:
                if fpts_2024 and fpts_2023 and fpts_2024 > fpts_2023 * 1.05:
                    return {
                        'trajectory': TRAJECTORY_RISING,
                        'confidence': 85,
                        'reason': 'Consistent improvement: 2023→2024→2025',
                        'trend': [fpts_2023, fpts_2024, fpts_2025]
                    }
                return {
                    'trajectory': TRAJECTORY_RISING,
                    'confidence': 70,
                    'reason': f'2025 ({fpts_2025:.0f}) up from 2024 ({fpts_2024:.0f})',
                    'delta': fpts_2025 - fpts_2024
                }

        # Declining: Consistent year-over-year drop
        if fpts_2025 and fpts_2024:
            if fpts_2025 < fpts_2024 * 0.92:
                if fpts_2024 and fpts_2023 and fpts_2024 < fpts_2023 * 0.92:
                    return {
                        'trajectory': TRAJECTORY_DECLINING,
                        'confidence': 85,
                        'reason': 'Consistent decline: 2023→2024→2025',
                        'trend': [fpts_2023, fpts_2024, fpts_2025]
                    }
                return {
                    'trajectory': TRAJECTORY_DECLINING,
                    'confidence': 70,
                    'reason': f'2025 ({fpts_2025:.0f}) down from 2024 ({fpts_2024:.0f})',
                    'delta': fpts_2025 - fpts_2024
                }

    # Bounceback: Bad 2025, good projection
    if fpts_2025 and fpts_2025 < avg_historical * 0.85:
        if fpts_proj > fpts_2025 * 1.20:
            return {
                'trajectory': TRAJECTORY_BOUNCE,
                'confidence': 65,
                'reason': f'Down year ({fpts_2025:.0f}) but projected recovery ({fpts_proj:.0f})',
                'delta': fpts_proj - fpts_2025
            }

    # Default: Steady
    return {
        'trajectory': TRAJECTORY_STEADY,
        'confidence': 60,
        'reason': 'Stable production expected'
    }


def calculate_consistency(player_id: int) -> dict:
    """Calculate consistency score (0-100, higher = more consistent).

    Based on coefficient of variation (CV) of historical FPTS.
    Lower CV = more consistent = higher score.
    """
    history = get_historical_fpts(player_id)

    years = []
    for key in ['fpts_2023', 'fpts_2024', 'fpts_2025']:
        val = history.get(key)
        if val is not None and val > 0:
            years.append(val)

    if len(years) < 2:
        return {
            'score': 50,
            'level': 'UNKNOWN',
            'reason': 'Insufficient data for consistency calculation'
        }

    avg = mean(years)
    std = stdev(years)

    # Coefficient of variation (std/mean)
    cv = std / avg if avg > 0 else 0

    # Convert to 0-100 score (lower CV = higher score)
    # CV of 0 = 100, CV of 0.5 = 0
    score = max(0, min(100, 100 - (cv * 200)))

    if score >= 80:
        level = 'ELITE'
    elif score >= 60:
        level = 'GOOD'
    elif score >= 40:
        level = 'AVERAGE'
    else:
        level = 'VOLATILE'

    return {
        'score': round(score, 1),
        'level': level,
        'cv': round(cv, 3),
        'avg_fpts': round(avg, 0),
        'std_dev': round(std, 0),
        'years': years
    }


def detect_age_curve_position(age: int, position: str) -> dict:
    """Determine where player is on typical age curve.

    Hitters peak 27-30, pitchers peak 26-29.
    """
    is_pitcher = position in ['SP', 'RP']

    if is_pitcher:
        peak_start, peak_end = 26, 29
    else:
        peak_start, peak_end = 27, 30

    if age < peak_start - 2:
        curve = 'PRE_PRIME'
        outlook = 'upside'
        modifier = 1.05  # Expect improvement
    elif age < peak_start:
        curve = 'APPROACHING_PRIME'
        outlook = 'improving'
        modifier = 1.02
    elif age <= peak_end:
        curve = 'PRIME'
        outlook = 'peak'
        modifier = 1.0
    elif age <= peak_end + 2:
        curve = 'POST_PRIME'
        outlook = 'maintaining'
        modifier = 0.98
    else:
        curve = 'DECLINING'
        outlook = 'declining'
        modifier = 0.95

    return {
        'curve': curve,
        'outlook': outlook,
        'modifier': modifier,
        'age': age,
        'peak_range': f'{peak_start}-{peak_end}'
    }


def get_player_insight(player_id: int) -> dict:
    """Get comprehensive insight for a single player."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.name, p.primary_position, p.mlb_team
        FROM players p
        WHERE p.id = ?
    """, (player_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    name, position, team = row

    trajectory = detect_trajectory(player_id)
    consistency = calculate_consistency(player_id)

    return {
        'player_id': player_id,
        'name': name,
        'position': position,
        'team': team,
        'trajectory': trajectory,
        'consistency': consistency,
    }


def get_breakout_candidates(limit: int = 20) -> list[dict]:
    """Find players with BREAKOUT trajectory."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.id, p.name, p.primary_position, p.mlb_team, proj.fpts
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        LEFT JOIN draft_picks dp ON p.id = dp.player_id
        WHERE proj.fpts > 300 AND dp.id IS NULL
        ORDER BY proj.fpts DESC
        LIMIT 100
    """)

    rows = cursor.fetchall()
    conn.close()

    candidates = []
    for row in rows:
        player_id = row[0]
        trajectory = detect_trajectory(player_id)

        if trajectory['trajectory'] == TRAJECTORY_BREAKOUT:
            candidates.append({
                'player_id': player_id,
                'name': row[1],
                'position': row[2],
                'team': row[3],
                'fpts_proj': row[4],
                **trajectory
            })

        if len(candidates) >= limit:
            break

    return candidates


def get_declining_players(limit: int = 20) -> list[dict]:
    """Find players with DECLINING trajectory."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.id, p.name, p.primary_position, p.mlb_team, proj.fpts
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        WHERE proj.fpts > 250
        ORDER BY proj.fpts DESC
        LIMIT 150
    """)

    rows = cursor.fetchall()
    conn.close()

    declining = []
    for row in rows:
        player_id = row[0]
        trajectory = detect_trajectory(player_id)

        if trajectory['trajectory'] == TRAJECTORY_DECLINING:
            declining.append({
                'player_id': player_id,
                'name': row[1],
                'position': row[2],
                'team': row[3],
                'fpts_proj': row[4],
                **trajectory
            })

        if len(declining) >= limit:
            break

    return declining


def get_bounceback_candidates(limit: int = 15) -> list[dict]:
    """Find players with BOUNCEBACK potential."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.id, p.name, p.primary_position, p.mlb_team, proj.fpts
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        LEFT JOIN draft_picks dp ON p.id = dp.player_id
        WHERE proj.fpts > 300 AND dp.id IS NULL
        ORDER BY proj.fpts DESC
        LIMIT 100
    """)

    rows = cursor.fetchall()
    conn.close()

    candidates = []
    for row in rows:
        player_id = row[0]
        trajectory = detect_trajectory(player_id)

        if trajectory['trajectory'] == TRAJECTORY_BOUNCE:
            candidates.append({
                'player_id': player_id,
                'name': row[1],
                'position': row[2],
                'team': row[3],
                'fpts_proj': row[4],
                **trajectory
            })

        if len(candidates) >= limit:
            break

    return candidates


if __name__ == "__main__":
    print("Player Insights Engine")
    print("=" * 60)

    print("\nBreakout Candidates:")
    breakouts = get_breakout_candidates(limit=10)
    for p in breakouts:
        print(f"  {p['name']} ({p['position']}): {p['reason']}")

    print("\nBounceback Candidates:")
    bounces = get_bounceback_candidates(limit=10)
    for p in bounces:
        print(f"  {p['name']} ({p['position']}): {p['reason']}")

    print("\nDeclining Players (avoid overpaying):")
    declining = get_declining_players(limit=10)
    for p in declining:
        print(f"  {p['name']} ({p['position']}): {p['reason']}")
