"""VORP (Value Over Replacement Player) Calculator.

VORP measures how many fantasy points a player contributes above
replacement level at their position. This is the core metric for
understanding true draft value.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.database import get_connection
from app.config import REPLACEMENT_FPTS, SALARY_CAP, NUM_TEAMS


def get_replacement_level(position: str) -> float:
    """Get the replacement level FPTS for a position.

    Replacement level = the FPTS of the last rosterable player at position.
    """
    return REPLACEMENT_FPTS.get(position, 250)


def calculate_vorp(player_fpts: float, position: str) -> float:
    """Calculate VORP for a single player.

    VORP = Player FPTS - Replacement Level FPTS

    Args:
        player_fpts: Player's projected or actual FPTS
        position: Primary position

    Returns:
        VORP value (can be negative for below-replacement players)
    """
    replacement = get_replacement_level(position)
    return player_fpts - replacement


def calculate_total_league_vorp() -> float:
    """Calculate total VORP available in the player pool.

    Used to determine dollars per VORP point.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.primary_position,
            SUM(proj.fpts)
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        LEFT JOIN draft_picks dp ON p.id = dp.player_id
        WHERE proj.fpts > 0 AND dp.id IS NULL
        GROUP BY p.primary_position
    """)

    total_vorp = 0
    for row in cursor.fetchall():
        pos = row[0] or 'DH'
        total_fpts = row[1] or 0
        replacement = get_replacement_level(pos)

        # Count rostered players at position
        cursor.execute("""
            SELECT COUNT(*) FROM players p
            JOIN projections proj ON p.id = proj.player_id
                AND proj.season = 2026 AND proj.stat_type = 'projection'
            WHERE p.positions LIKE ? AND proj.fpts > ?
        """, (f'%{pos}%', replacement))

        rosterable = cursor.fetchone()[0]

        # VORP is sum of (player_fpts - replacement) for rostered players
        cursor.execute("""
            SELECT SUM(proj.fpts - ?)
            FROM players p
            JOIN projections proj ON p.id = proj.player_id
                AND proj.season = 2026 AND proj.stat_type = 'projection'
            WHERE p.positions LIKE ? AND proj.fpts > ?
        """, (replacement, f'%{pos}%', replacement))

        pos_vorp = cursor.fetchone()[0] or 0
        total_vorp += pos_vorp

    conn.close()
    return total_vorp


def calculate_dollars_per_vorp() -> float:
    """Calculate how much each VORP point is worth in auction dollars.

    Total Auction Pool / Total Available VORP = $/VORP
    """
    total_pool = SALARY_CAP * NUM_TEAMS  # Total auction dollars
    total_vorp = calculate_total_league_vorp()

    if total_vorp <= 0:
        return 0.05  # Fallback

    return total_pool / total_vorp


def calculate_vorp_value(player_fpts: float, position: str) -> float:
    """Calculate auction value based on VORP.

    Args:
        player_fpts: Player's projected FPTS
        position: Primary position

    Returns:
        Estimated auction value in dollars
    """
    vorp = calculate_vorp(player_fpts, position)
    dollars_per = calculate_dollars_per_vorp()

    # Negative VORP = $1 (minimum bid)
    if vorp <= 0:
        return 1

    return max(1, round(vorp * dollars_per))


def calculate_all_vorp():
    """Calculate and store VORP for all players."""
    conn = get_connection()
    cursor = conn.cursor()

    # Add VORP column to pb_scores if not exists
    cursor.execute("""
        SELECT COUNT(*) FROM pragma_table_info('pb_scores')
        WHERE name = 'vorp'
    """)
    if cursor.fetchone()[0] == 0:
        cursor.execute("ALTER TABLE pb_scores ADD COLUMN vorp REAL")
        cursor.execute("ALTER TABLE pb_scores ADD COLUMN vorp_value REAL")

    # Get all players
    cursor.execute("""
        SELECT p.id, p.primary_position, proj.fpts
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        WHERE proj.fpts IS NOT NULL
    """)

    players = cursor.fetchall()
    dollars_per = calculate_dollars_per_vorp()

    for player in players:
        player_id, position, fpts = player
        position = position or 'DH'

        vorp = calculate_vorp(fpts, position)
        vorp_value = max(1, round(vorp * dollars_per)) if vorp > 0 else 1

        cursor.execute("""
            UPDATE pb_scores SET vorp = ?, vorp_value = ? WHERE player_id = ?
        """, (vorp, vorp_value, player_id))

    conn.commit()
    conn.close()

    return len(players)


def get_top_vorp_players(position: str = None, limit: int = 25) -> list[dict]:
    """Get players with highest VORP."""
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            p.id, p.name, p.mlb_team, p.primary_position,
            proj.fpts,
            pb.vorp, pb.vorp_value, pb.pb_score, pb.value_gap
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        JOIN pb_scores pb ON p.id = pb.player_id
        LEFT JOIN draft_picks dp ON p.id = dp.player_id
        WHERE pb.vorp IS NOT NULL AND dp.id IS NULL
    """

    params = []
    if position:
        query += " AND p.positions LIKE ?"
        params.append(f'%{position}%')

    query += " ORDER BY pb.vorp DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            'player_id': row[0],
            'name': row[1],
            'team': row[2],
            'position': row[3],
            'fpts': row[4],
            'vorp': row[5],
            'vorp_value': row[6],
            'pb_score': row[7],
            'value_gap': row[8],
        }
        for row in rows
    ]


def get_vorp_summary() -> dict:
    """Get VORP summary statistics."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.primary_position,
            COUNT(*),
            AVG(pb.vorp),
            MAX(pb.vorp),
            SUM(pb.vorp)
        FROM players p
        JOIN pb_scores pb ON p.id = pb.player_id
        WHERE pb.vorp > 0
        GROUP BY p.primary_position
        ORDER BY SUM(pb.vorp) DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return {
        'by_position': {
            row[0] or 'DH': {
                'count': row[1],
                'avg_vorp': round(row[2], 1) if row[2] else 0,
                'max_vorp': round(row[3], 1) if row[3] else 0,
                'total_vorp': round(row[4], 1) if row[4] else 0,
            }
            for row in rows
        },
        'dollars_per_vorp': round(calculate_dollars_per_vorp(), 3),
    }


if __name__ == "__main__":
    print("VORP Calculator")
    print("=" * 60)

    print("\nCalculating VORP for all players...")
    count = calculate_all_vorp()
    print(f"Processed {count} players")

    print("\nVORP Summary:")
    summary = get_vorp_summary()
    print(f"  Dollars per VORP: ${summary['dollars_per_vorp']:.3f}")

    print("\nBy Position:")
    for pos, data in summary['by_position'].items():
        print(f"  {pos}: {data['count']} players, avg VORP {data['avg_vorp']}, "
              f"max {data['max_vorp']}, total {data['total_vorp']}")

    print("\nTop 15 VORP Players:")
    top = get_top_vorp_players(limit=15)
    for i, p in enumerate(top, 1):
        print(f"  {i:2}. {p['name']} ({p['position']}): "
              f"VORP {p['vorp']:.0f} = ${p['vorp_value']:.0f} | "
              f"PB: {p['pb_score']:.0f}")
