"""Position tiers engine - calculate tier assignments and bidding ranges."""
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.database import get_connection
from model.ab_score import ABScoreCalculator, calculate_auction_value, calculate_bid_range
from app.config import TIER_CUTOFFS, POSITIONAL_SCARCITY


def calculate_dynamic_tier_cutoffs(position: str) -> list[float]:
    """Calculate tier cutoffs based on actual data distribution.

    Returns [tier1_min, tier2_min, tier3_min] - FPTS thresholds

    Tier sizing is position-dependent for fantasy relevance:
    - Tier 1: Elite (top 5-15 players you'd pay premium for)
    - Tier 2: Solid starters (next 15-30 players, good value)
    - Tier 3: Acceptable (next 20-40 players, streamers/depth)
    - Tier 4: Replacement level (everyone else)
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get FPTS distribution for this position (only meaningful projections)
    cursor.execute("""
        SELECT proj.fpts
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
        WHERE p.positions LIKE ? AND proj.season = 2026
            AND proj.stat_type = 'projection' AND proj.fpts > 50
        ORDER BY proj.fpts DESC
    """, (f'%{position}%',))

    fpts_list = [row[0] for row in cursor.fetchall()]
    conn.close()

    if not fpts_list:
        return TIER_CUTOFFS.get(position, [400, 300, 200])

    # Position-specific tier sizes (how many fantasy-relevant players per tier)
    tier_counts = {
        'C': (5, 10, 15),      # Shallow position
        '1B': (8, 15, 25),
        '2B': (10, 20, 30),
        '3B': (8, 15, 25),
        'SS': (10, 20, 30),
        'OF': (15, 35, 50),    # Deep position (3 slots)
        'DH': (5, 10, 15),
        'SP': (20, 40, 60),    # Deep (4-5 slots)
        'RP': (15, 30, 50),
    }

    t1_count, t2_count, t3_count = tier_counts.get(position, (10, 25, 40))

    n = len(fpts_list)
    tier1_idx = min(t1_count - 1, n - 1)
    tier2_idx = min(t1_count + t2_count - 1, n - 1)
    tier3_idx = min(t1_count + t2_count + t3_count - 1, n - 1)

    return [
        fpts_list[tier1_idx],
        fpts_list[tier2_idx],
        fpts_list[tier3_idx],
    ]


def get_tier(fpts: float, cutoffs: list[float]) -> int:
    """Determine tier based on FPTS and cutoffs."""
    if fpts >= cutoffs[0]:
        return 1
    elif fpts >= cutoffs[1]:
        return 2
    elif fpts >= cutoffs[2]:
        return 3
    else:
        return 4


def calculate_all_tiers_and_scores():
    """Calculate and store tiers and AB Scores for all players."""
    conn = get_connection()
    cursor = conn.cursor()

    calc = ABScoreCalculator()

    # Get all positions
    positions = ['C', '1B', '2B', '3B', 'SS', 'OF', 'DH', 'SP', 'RP']

    for position in positions:
        print(f"Processing {position}...")

        # Get dynamic cutoffs
        cutoffs = calculate_dynamic_tier_cutoffs(position)
        print(f"  Cutoffs: Tier1 >= {cutoffs[0]:.0f}, Tier2 >= {cutoffs[1]:.0f}, Tier3 >= {cutoffs[2]:.0f}")

        # Get all players at this position with their projections
        cursor.execute("""
            SELECT
                p.id, p.name, p.mlb_team, p.positions,
                proj.fpts, proj.gs, proj.app,
                stats25.fpts as fpts_2025
            FROM players p
            JOIN projections proj ON p.id = proj.player_id
                AND proj.season = 2026 AND proj.stat_type = 'projection'
            LEFT JOIN projections stats25 ON p.id = stats25.player_id
                AND stats25.season = 2025 AND stats25.stat_type = 'actual'
            WHERE p.positions LIKE ? AND proj.fpts IS NOT NULL
            ORDER BY proj.fpts DESC
        """, (f'%{position}%',))

        players = cursor.fetchall()
        rank_in_tier = {1: 0, 2: 0, 3: 0, 4: 0}

        for player in players:
            player_id = player[0]
            name = player[1]
            team = player[2] or 'FA'
            positions_str = player[3] or position
            fpts_proj = player[4] or 0
            gs = player[5]  # games started (pitchers)
            app = player[6]  # appearances
            fpts_2025 = player[7]

            positions_list = [p.strip() for p in positions_str.split(',')]
            is_pitcher = position in ['SP', 'RP']

            # Determine tier
            tier = get_tier(fpts_proj, cutoffs)
            rank_in_tier[tier] += 1

            # Calculate AB Score
            result = calc.calculate_ab_score(
                positions=positions_list,
                fpts_proj=fpts_proj,
                team=team,
                lineup_slot=rank_in_tier[tier],  # Use rank as proxy for lineup slot
                games_2025=gs if is_pitcher else None,
                fpts_2025=fpts_2025,
                is_pitcher=is_pitcher,
            )

            ab_score = result['ab_score']
            auction_value = calculate_auction_value(ab_score, position)
            floor, target, ceiling = calculate_bid_range(auction_value)

            # Store tier
            cursor.execute("""
                INSERT OR REPLACE INTO position_tiers
                (player_id, position, tier, rank_in_tier, bid_floor, bid_target, bid_ceiling)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (player_id, position, tier, rank_in_tier[tier], floor, target, ceiling))

            # Store AB Score
            cursor.execute("""
                INSERT OR REPLACE INTO ab_scores
                (player_id, scarcity, slot, fpts_score, durability,
                 team_quality, multi_pos, value_gap, health, contract,
                 ab_score, auction_value)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                player_id,
                result['components']['scarcity'],
                result['components']['slot'],
                result['components']['fpts'],
                result['components']['durability'],
                result['components']['team_quality'],
                result['components']['multi_pos'],
                result['components']['value_gap'],
                result['components']['health'],
                result['components']['contract'],
                ab_score,
                auction_value
            ))

        print(f"  Tier counts: T1={rank_in_tier[1]}, T2={rank_in_tier[2]}, T3={rank_in_tier[3]}, T4={rank_in_tier[4]}")

    conn.commit()
    conn.close()
    print("\nAll tiers and scores calculated!")


def get_position_tiers(position: str, limit_per_tier: int = 20) -> dict:
    """Get players organized by tier for a position."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.id, p.name, p.mlb_team, p.positions,
            proj.fpts, proj.hr, proj.rbi, proj.sb, proj.avg,
            proj.w, proj.sv, proj.k_pitch, proj.era,
            ab.ab_score, ab.auction_value,
            pt.tier, pt.rank_in_tier, pt.bid_floor, pt.bid_target, pt.bid_ceiling
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        JOIN ab_scores ab ON p.id = ab.player_id
        JOIN position_tiers pt ON p.id = pt.player_id AND pt.position = ?
        WHERE p.positions LIKE ?
        ORDER BY pt.tier, pt.rank_in_tier
    """, (position, f'%{position}%'))

    rows = cursor.fetchall()
    conn.close()

    tiers = {1: [], 2: [], 3: [], 4: []}

    for row in rows:
        player = {
            'id': row[0],
            'name': row[1],
            'team': row[2],
            'positions': row[3],
            'fpts': row[4],
            'hr': row[5],
            'rbi': row[6],
            'sb': row[7],
            'avg': row[8],
            'w': row[9],
            'sv': row[10],
            'k': row[11],
            'era': row[12],
            'ab_score': row[13],
            'auction_value': row[14],
            'tier': row[15],
            'rank': row[16],
            'bid_floor': row[17],
            'bid_target': row[18],
            'bid_ceiling': row[19],
        }
        tier = player['tier']
        if len(tiers[tier]) < limit_per_tier:
            tiers[tier].append(player)

    return tiers


def get_tier_summary() -> dict:
    """Get summary of tier distribution across all positions."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT position, tier, COUNT(*) as count
        FROM position_tiers
        GROUP BY position, tier
        ORDER BY position, tier
    """)

    rows = cursor.fetchall()
    conn.close()

    summary = {}
    for row in rows:
        pos, tier, count = row
        if pos not in summary:
            summary[pos] = {}
        summary[pos][tier] = count

    return summary


if __name__ == "__main__":
    calculate_all_tiers_and_scores()
    print("\nTier Summary:")
    summary = get_tier_summary()
    for pos, tiers in summary.items():
        print(f"  {pos}: {tiers}")
