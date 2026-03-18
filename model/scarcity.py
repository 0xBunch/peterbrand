"""Scarcity Analyzer - Talent cliff detection and position urgency.

Identifies where talent drops sharply at each position and provides
timing recommendations for when to target positions during the draft.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.database import get_connection
from app.config import CLIFF_THRESHOLD_PCT, ROSTER_SLOTS, REPLACEMENT_FPTS


def find_talent_cliffs(position: str) -> list[dict]:
    """Find where talent drops sharply at a position.

    A "cliff" is where FPTS drops by more than CLIFF_THRESHOLD_PCT
    between consecutive players.

    Returns:
        List of cliff points with recommendations
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.id, p.name, proj.fpts
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        LEFT JOIN draft_picks dp ON p.id = dp.player_id
        WHERE p.positions LIKE ? AND proj.fpts IS NOT NULL AND dp.id IS NULL
        ORDER BY proj.fpts DESC
    """, (f'%{position}%',))

    players = cursor.fetchall()
    conn.close()

    cliffs = []
    for i in range(len(players) - 1):
        current = players[i]
        next_player = players[i + 1]

        current_fpts = current[2]
        next_fpts = next_player[2]

        if current_fpts <= 0:
            continue

        fpts_drop = current_fpts - next_fpts
        pct_drop = fpts_drop / current_fpts

        if pct_drop >= CLIFF_THRESHOLD_PCT:
            cliffs.append({
                'rank': i + 1,
                'after_player': current[1],
                'after_fpts': current_fpts,
                'before_player': next_player[1],
                'before_fpts': next_fpts,
                'fpts_drop': round(fpts_drop, 0),
                'pct_drop': round(pct_drop * 100, 1),
                'severity': 'MAJOR' if pct_drop >= 0.15 else 'MINOR',
                'recommendation': f"Target {position} before #{i + 2} overall"
            })

    return cliffs


def get_undrafted_count(position: str) -> int:
    """Count undrafted players at a position above replacement level."""
    conn = get_connection()
    cursor = conn.cursor()

    replacement = REPLACEMENT_FPTS.get(position, 200)

    cursor.execute("""
        SELECT COUNT(*)
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        LEFT JOIN draft_picks dp ON p.id = dp.player_id
        WHERE p.positions LIKE ? AND proj.fpts > ? AND dp.id IS NULL
    """, (f'%{position}%', replacement))

    count = cursor.fetchone()[0]
    conn.close()
    return count


def calculate_position_urgency(position: str, current_round: int = 1, total_rounds: int = 23) -> dict:
    """Calculate how urgent it is to fill a position.

    Higher urgency = need to act soon (supply dwindling or need unfilled)

    Returns:
        Dict with urgency score (0-100) and explanation
    """
    needed = ROSTER_SLOTS.get(position, {}).get('needed', 1)
    undrafted = get_undrafted_count(position)
    remaining_rounds = max(1, total_rounds - current_round)

    # Already filled
    if needed <= 0:
        return {
            'urgency': 0,
            'level': 'FILLED',
            'explanation': f'{position} roster spots filled'
        }

    # No supply left
    if undrafted <= 0:
        return {
            'urgency': 100,
            'level': 'CRITICAL',
            'explanation': f'No rosterable {position} remaining!'
        }

    # Urgency formula: need / (supply * time)
    # Scaled to 0-100
    supply_ratio = undrafted / max(1, needed * 10)  # Compare to 10x need
    time_ratio = remaining_rounds / total_rounds

    # Low supply or low time = high urgency
    urgency = 100 - (supply_ratio * time_ratio * 100)
    urgency = max(0, min(100, urgency))

    # Find next cliff
    cliffs = find_talent_cliffs(position)
    cliff_warning = None
    for cliff in cliffs[:3]:  # Check top 3 cliffs
        if cliff['rank'] <= undrafted:
            cliff_warning = f"Cliff after {cliff['after_player']}"
            urgency = min(100, urgency + 15)
            break

    # Determine level
    if urgency >= 80:
        level = 'CRITICAL'
    elif urgency >= 60:
        level = 'HIGH'
    elif urgency >= 40:
        level = 'MODERATE'
    else:
        level = 'LOW'

    explanation = f"Need {needed} {position}, {undrafted} remaining above replacement"
    if cliff_warning:
        explanation += f" | {cliff_warning}"

    return {
        'urgency': round(urgency, 1),
        'level': level,
        'needed': needed,
        'undrafted': undrafted,
        'cliff_warning': cliff_warning,
        'explanation': explanation
    }


def get_scarcity_alerts(current_round: int = 1) -> list[dict]:
    """Get all scarcity alerts sorted by urgency.

    Returns alerts for positions with HIGH or CRITICAL urgency.
    """
    positions = ['C', '1B', '2B', '3B', 'SS', 'OF', 'DH', 'SP', 'RP']
    alerts = []

    for pos in positions:
        urgency = calculate_position_urgency(pos, current_round)
        if urgency['level'] in ['CRITICAL', 'HIGH']:
            alerts.append({
                'position': pos,
                **urgency
            })

    # Sort by urgency descending
    alerts.sort(key=lambda x: x['urgency'], reverse=True)
    return alerts


def get_position_depth_chart(position: str, limit: int = 15) -> list[dict]:
    """Get depth chart for a position showing tiers and cliffs."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.id, p.name, p.mlb_team, proj.fpts,
            pt.tier, pt.bid_target, pb.pb_score
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        LEFT JOIN position_tiers pt ON p.id = pt.player_id AND pt.position = ?
        LEFT JOIN pb_scores pb ON p.id = pb.player_id
        LEFT JOIN draft_picks dp ON p.id = dp.player_id
        WHERE p.positions LIKE ? AND proj.fpts IS NOT NULL AND dp.id IS NULL
        ORDER BY proj.fpts DESC
        LIMIT ?
    """, (position, f'%{position}%', limit))

    rows = cursor.fetchall()
    conn.close()

    cliffs = find_talent_cliffs(position)
    cliff_ranks = {c['rank'] for c in cliffs}

    depth = []
    for i, row in enumerate(rows):
        depth.append({
            'rank': i + 1,
            'player_id': row[0],
            'name': row[1],
            'team': row[2],
            'fpts': row[3],
            'tier': row[4] or 4,
            'bid_target': row[5] or 1,
            'pb_score': row[6] or 0,
            'is_cliff': (i + 1) in cliff_ranks,
        })

    return depth


def get_scarcity_summary() -> dict:
    """Get summary of scarcity across all positions."""
    positions = ['C', '1B', '2B', '3B', 'SS', 'OF', 'DH', 'SP', 'RP']

    summary = {}
    for pos in positions:
        urgency = calculate_position_urgency(pos)
        cliffs = find_talent_cliffs(pos)

        summary[pos] = {
            'urgency': urgency['urgency'],
            'level': urgency['level'],
            'undrafted': urgency.get('undrafted', 0),
            'needed': urgency.get('needed', 0),
            'cliff_count': len(cliffs),
            'first_cliff': cliffs[0] if cliffs else None,
        }

    return summary


def get_scarcity_multiplier(position: str) -> float:
    """Get a scarcity multiplier for a position based on remaining supply.

    The multiplier increases as supply decreases relative to demand.

    Returns:
        float multiplier (1.0 = normal, 1.5 = 50% premium, etc.)
    """
    urgency = calculate_position_urgency(position)

    # Map urgency (0-100) to multiplier (1.0 - 1.5)
    # 0 urgency = 1.0x, 100 urgency = 1.5x
    multiplier = 1.0 + (urgency['urgency'] / 200)

    return multiplier


def get_all_scarcity_multipliers() -> dict:
    """Get scarcity multipliers for all positions."""
    positions = ['C', '1B', '2B', '3B', 'SS', 'OF', 'DH', 'SP', 'RP']
    return {pos: get_scarcity_multiplier(pos) for pos in positions}


if __name__ == "__main__":
    print("Scarcity Analyzer")
    print("=" * 60)

    print("\nPosition Scarcity Summary:")
    summary = get_scarcity_summary()
    for pos, data in summary.items():
        cliff_info = f" | Cliff after #{data['first_cliff']['rank']}" if data['first_cliff'] else ""
        print(f"  {pos}: Urgency {data['urgency']:.0f} ({data['level']}) "
              f"- {data['undrafted']} available, need {data['needed']}{cliff_info}")

    print("\nScarcity Alerts (HIGH/CRITICAL only):")
    alerts = get_scarcity_alerts()
    if alerts:
        for alert in alerts:
            print(f"  [{alert['level']}] {alert['position']}: {alert['explanation']}")
    else:
        print("  No critical alerts")

    print("\nTalent Cliffs by Position:")
    for pos in ['3B', 'C', 'SS', 'SP']:  # Key positions
        cliffs = find_talent_cliffs(pos)
        print(f"\n  {pos}:")
        for cliff in cliffs[:3]:
            print(f"    Rank {cliff['rank']}: {cliff['after_player']} ({cliff['after_fpts']:.0f}) "
                  f"→ {cliff['before_player']} ({cliff['before_fpts']:.0f}) "
                  f"[{cliff['severity']}: -{cliff['pct_drop']}%]")
