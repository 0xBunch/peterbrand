"""Roster Optimizer - Linear programming for optimal team construction.

Uses integer linear programming to find the roster that maximizes
total projected FPTS within budget and roster constraints.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.database import get_connection
from app.config import ROSTER_SLOTS, SALARY_CAP, AVAILABLE_BUDGET

# Try to import PuLP, fall back to greedy algorithm if not available
try:
    from pulp import LpMaximize, LpProblem, LpVariable, lpSum, LpStatus
    HAS_PULP = True
except ImportError:
    HAS_PULP = False
    print("Warning: PuLP not installed. Using greedy optimizer instead.")


def get_available_players() -> list[dict]:
    """Get all undrafted players with their projections and bids."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.id, p.name, p.positions, p.primary_position, p.mlb_team,
            proj.fpts,
            pt.tier, pt.bid_target, pt.max_bid,
            pb.pb_score, pb.vorp
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        LEFT JOIN position_tiers pt ON p.id = pt.player_id
            AND pt.position = p.primary_position
        LEFT JOIN pb_scores pb ON p.id = pb.player_id
        LEFT JOIN draft_picks dp ON p.id = dp.player_id
        WHERE proj.fpts > 100 AND dp.id IS NULL
        ORDER BY proj.fpts DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    players = []
    for row in rows:
        positions = row[2] or row[3] or 'DH'
        pos_list = [p.strip() for p in positions.split(',') if p.strip()]

        players.append({
            'id': row[0],
            'name': row[1],
            'positions': pos_list,
            'primary_position': row[3] or 'DH',
            'team': row[4],
            'fpts': row[5] or 0,
            'tier': row[6] or 4,
            'cost': row[7] or 1,
            'max_bid': row[8] or 50,
            'pb_score': row[9] or 0,
            'vorp': row[10] or 0,
        })

    return players


def optimize_roster_pulp(budget: int, roster_needs: dict, players: list = None) -> dict:
    """Use PuLP for optimal roster construction.

    Args:
        budget: Available auction dollars
        roster_needs: Dict of position -> slots needed
        players: Optional player list (fetches if None)

    Returns:
        Dict with optimal roster, total FPTS, total cost
    """
    if not HAS_PULP:
        return optimize_roster_greedy(budget, roster_needs, players)

    if players is None:
        players = get_available_players()

    # Filter players that cost more than budget
    players = [p for p in players if p['cost'] <= budget]

    if not players:
        return {'roster': [], 'total_fpts': 0, 'total_cost': 0, 'success': False}

    # Create problem
    prob = LpProblem("Fantasy_Roster", LpMaximize)

    # Decision variables: 1 if player selected, 0 otherwise
    player_vars = {p['id']: LpVariable(f"player_{p['id']}", cat='Binary')
                   for p in players}

    # Objective: Maximize total FPTS
    prob += lpSum(p['fpts'] * player_vars[p['id']] for p in players)

    # Constraint: Total cost <= budget
    prob += lpSum(p['cost'] * player_vars[p['id']] for p in players) <= budget

    # Constraint: Each position slot filled
    for pos, needed in roster_needs.items():
        if needed <= 0:
            continue

        eligible = [p for p in players if pos in p['positions']]
        if eligible:
            prob += lpSum(player_vars[p['id']] for p in eligible) >= needed

    # Constraint: Each player selected at most once
    for p in players:
        prob += player_vars[p['id']] <= 1

    # Solve
    prob.solve()

    if LpStatus[prob.status] != 'Optimal':
        return {'roster': [], 'total_fpts': 0, 'total_cost': 0, 'success': False}

    # Extract solution
    selected = []
    for p in players:
        if player_vars[p['id']].varValue == 1:
            selected.append(p)

    total_fpts = sum(p['fpts'] for p in selected)
    total_cost = sum(p['cost'] for p in selected)

    return {
        'roster': selected,
        'total_fpts': total_fpts,
        'total_cost': total_cost,
        'budget_remaining': budget - total_cost,
        'success': True,
        'method': 'linear_programming'
    }


def optimize_roster_greedy(budget: int, roster_needs: dict, players: list = None) -> dict:
    """Greedy optimizer fallback when PuLP not available.

    Fills positions by best FPTS/$ ratio while respecting budget.
    """
    if players is None:
        players = get_available_players()

    # Sort by FPTS/cost ratio
    for p in players:
        p['efficiency'] = p['fpts'] / max(1, p['cost'])

    available = sorted(players, key=lambda x: x['efficiency'], reverse=True)
    selected = []
    remaining_budget = budget
    filled = {pos: 0 for pos in roster_needs}

    # Fill each position need
    for pos, needed in roster_needs.items():
        if needed <= 0:
            continue

        for _ in range(needed):
            # Find best affordable player for position
            for p in available:
                if pos in p['positions'] and p['cost'] <= remaining_budget:
                    if p not in selected:
                        selected.append(p)
                        remaining_budget -= p['cost']
                        filled[pos] += 1
                        available.remove(p)
                        break

    total_fpts = sum(p['fpts'] for p in selected)
    total_cost = sum(p['cost'] for p in selected)

    return {
        'roster': selected,
        'total_fpts': total_fpts,
        'total_cost': total_cost,
        'budget_remaining': budget - total_cost,
        'success': True,
        'method': 'greedy'
    }


def optimize_roster(budget: int = None, roster_needs: dict = None) -> dict:
    """Main optimization function.

    Args:
        budget: Available auction dollars (default: AVAILABLE_BUDGET)
        roster_needs: Position needs (default: from ROSTER_SLOTS)

    Returns:
        Optimized roster solution
    """
    if budget is None:
        budget = AVAILABLE_BUDGET

    if roster_needs is None:
        roster_needs = {pos: info['needed'] for pos, info in ROSTER_SLOTS.items()}

    if HAS_PULP:
        return optimize_roster_pulp(budget, roster_needs)
    else:
        return optimize_roster_greedy(budget, roster_needs)


def calculate_remaining_optimal(
    current_roster: list[dict],
    remaining_budget: int,
    roster_needs: dict
) -> dict:
    """Calculate optimal roster given current draft state.

    Use case: "If I draft Soto at $45, what's my optimal remaining roster?"
    """
    return optimize_roster(remaining_budget, roster_needs)


def what_if_analysis(player_id: int, salary: int) -> dict:
    """Analyze impact of drafting a specific player at a given salary.

    Returns optimal remaining roster if you draft this player.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get player info
    cursor.execute("""
        SELECT p.name, p.primary_position, proj.fpts
        FROM players p
        JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        WHERE p.id = ?
    """, (player_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    name, position, fpts = row

    # Calculate remaining needs
    roster_needs = {pos: info['needed'] for pos, info in ROSTER_SLOTS.items()}
    roster_needs[position] = max(0, roster_needs.get(position, 0) - 1)

    remaining_budget = AVAILABLE_BUDGET - salary

    # Get all players except this one
    players = [p for p in get_available_players() if p['id'] != player_id]

    # Optimize remaining
    optimal = optimize_roster_pulp(remaining_budget, roster_needs, players) if HAS_PULP \
        else optimize_roster_greedy(remaining_budget, roster_needs, players)

    return {
        'player': {
            'id': player_id,
            'name': name,
            'position': position,
            'fpts': fpts,
            'cost': salary,
        },
        'remaining_optimal': optimal,
        'total_fpts': fpts + optimal['total_fpts'],
        'total_cost': salary + optimal['total_cost'],
    }


def get_optimal_by_position() -> dict:
    """Get optimal single player for each position need."""
    roster_needs = {pos: info['needed'] for pos, info in ROSTER_SLOTS.items()}
    players = get_available_players()

    optimal_by_pos = {}
    for pos, needed in roster_needs.items():
        if needed <= 0:
            continue

        eligible = [p for p in players if pos in p['positions']]
        eligible.sort(key=lambda x: x['fpts'], reverse=True)

        optimal_by_pos[pos] = eligible[:needed * 3]  # Top 3x needed

    return optimal_by_pos


if __name__ == "__main__":
    print("Roster Optimizer")
    print("=" * 60)

    print(f"\nOptimizer method: {'PuLP (Linear Programming)' if HAS_PULP else 'Greedy'}")

    print(f"\nOptimizing roster with budget ${AVAILABLE_BUDGET}...")
    result = optimize_roster()

    if result['success']:
        print(f"\nOptimal Roster ({result['method']}):")
        print(f"  Total FPTS: {result['total_fpts']:.0f}")
        print(f"  Total Cost: ${result['total_cost']}")
        print(f"  Remaining: ${result['budget_remaining']}")

        print("\n  Players:")
        for p in sorted(result['roster'], key=lambda x: x['fpts'], reverse=True):
            print(f"    {p['name']} ({p['primary_position']}): "
                  f"{p['fpts']:.0f} FPTS @ ${p['cost']}")
    else:
        print("  Optimization failed - no feasible solution")

    # What-if example
    print("\n" + "=" * 60)
    print("What-if Analysis: Draft top player at bid target")

    players = get_available_players()
    if players:
        top = players[0]
        analysis = what_if_analysis(top['id'], top['cost'])
        if analysis:
            print(f"\nIf you draft {top['name']} at ${top['cost']}:")
            print(f"  His FPTS: {analysis['player']['fpts']:.0f}")
            print(f"  Remaining optimal FPTS: {analysis['remaining_optimal']['total_fpts']:.0f}")
            print(f"  Total team FPTS: {analysis['total_fpts']:.0f}")
