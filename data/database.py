"""Database setup and queries for Austin Bats / Peter Brand"""
import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent.parent / "db" / "peterbrand.db"


def get_connection() -> sqlite3.Connection:
    """Get database connection with row factory for dict-like access."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database schema."""
    conn = get_connection()
    cursor = conn.cursor()

    # Players table - core player identity
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mlb_team TEXT,
            positions TEXT,
            primary_position TEXT,
            UNIQUE(name, mlb_team)
        )
    """)

    # Projections and historical stats (multi-year)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            stat_type TEXT NOT NULL,
            -- Hitter stats
            ab INTEGER, r INTEGER, h INTEGER,
            singles INTEGER, doubles INTEGER, triples INTEGER,
            hr INTEGER, rbi INTEGER, bb INTEGER, k INTEGER,
            sb INTEGER, cs INTEGER,
            avg REAL, obp REAL, slg REAL,
            -- Pitcher stats
            ip REAL, app INTEGER, gs INTEGER, qs INTEGER, cg INTEGER,
            w INTEGER, l INTEGER, sv INTEGER, bs INTEGER, hd INTEGER,
            k_pitch INTEGER, bb_pitch INTEGER, h_pitch INTEGER,
            era REAL, whip REAL,
            -- Fantasy points
            fpts REAL,
            FOREIGN KEY (player_id) REFERENCES players(id),
            UNIQUE(player_id, season, stat_type)
        )
    """)

    # Position tiers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS position_tiers (
            player_id INTEGER NOT NULL,
            position TEXT NOT NULL,
            tier INTEGER NOT NULL,
            rank_in_tier INTEGER,
            bid_floor INTEGER,
            bid_target INTEGER,
            bid_ceiling INTEGER,
            FOREIGN KEY (player_id) REFERENCES players(id),
            PRIMARY KEY (player_id, position)
        )
    """)

    # PB Score components (Peter Brand Score)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pb_scores (
            player_id INTEGER PRIMARY KEY,
            -- Component scores (0-100 scale)
            historical_fpts REAL,
            league_value_gap REAL,
            positional_scarcity REAL,
            consistency REAL,
            team_context REAL,
            durability REAL,
            -- Computed values
            pb_score REAL,
            true_value REAL,
            league_price REAL,
            value_gap REAL,
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    """)

    # Historical stats (3-year averages for quick lookup)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_history (
            player_id INTEGER PRIMARY KEY,
            fpts_2023 REAL,
            fpts_2024 REAL,
            fpts_2025 REAL,
            fpts_3ya REAL,
            games_2023 INTEGER,
            games_2024 INTEGER,
            games_2025 INTEGER,
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    """)

    # Scouting notes - free-form player observations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scouting_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            note TEXT NOT NULL,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            season INTEGER,
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    """)

    # Opponent rosters - track who owns what
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS opponent_rosters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            salary INTEGER,
            position_slot TEXT,
            season INTEGER NOT NULL,
            FOREIGN KEY (player_id) REFERENCES players(id),
            UNIQUE(team, player_id, season)
        )
    """)

    # Draft history archive - historical draft prices by player
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS draft_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            season INTEGER NOT NULL,
            player_name TEXT NOT NULL,
            player_id INTEGER,
            team TEXT NOT NULL,
            position TEXT,
            salary INTEGER,
            fpts_total REAL,
            fpts_active REAL,
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    """)

    # League price calibration - aggregated position/tier prices
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS league_prices (
            position TEXT NOT NULL,
            tier INTEGER NOT NULL,
            avg_salary REAL,
            avg_fpts REAL,
            dollars_per_fpts REAL,
            sample_size INTEGER,
            PRIMARY KEY (position, tier)
        )
    """)

    # Current draft tracker
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS draft_picks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            team TEXT NOT NULL,
            salary INTEGER NOT NULL,
            pick_order INTEGER,
            is_keeper BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    """)

    # League teams
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS league_teams (
            name TEXT PRIMARY KEY,
            budget_remaining INTEGER DEFAULT 320,
            players_drafted INTEGER DEFAULT 0,
            tendency TEXT,
            notes TEXT
        )
    """)

    # Top prospects tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prospects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mlb_team TEXT,
            position TEXT,
            eta TEXT,
            ceiling TEXT,
            notes TEXT,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, mlb_team)
        )
    """)

    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")


def get_player_id(name: str, mlb_team: str, conn: sqlite3.Connection) -> int:
    """Get or create player ID."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM players WHERE name = ? AND mlb_team = ?",
        (name, mlb_team)
    )
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute(
        "INSERT INTO players (name, mlb_team) VALUES (?, ?)",
        (name, mlb_team)
    )
    return cursor.lastrowid


def get_player_by_name(name: str) -> Optional[dict]:
    """Get player by name (fuzzy match)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM players WHERE name LIKE ?
    """, (f"%{name}%",))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_players(position: Optional[str] = None) -> list[dict]:
    """Get all players with their projections and scores."""
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            p.id, p.name, p.mlb_team, p.positions, p.primary_position,
            proj.fpts, proj.ab, proj.hr, proj.rbi, proj.sb, proj.avg,
            proj.ip, proj.w, proj.sv, proj.k_pitch, proj.era,
            pb.pb_score, pb.true_value, pb.value_gap,
            pt.tier, pt.bid_floor, pt.bid_target, pt.bid_ceiling,
            ph.fpts_2023, ph.fpts_2024, ph.fpts_2025, ph.fpts_3ya
        FROM players p
        LEFT JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        LEFT JOIN pb_scores pb ON p.id = pb.player_id
        LEFT JOIN position_tiers pt ON p.id = pt.player_id
            AND pt.position = p.primary_position
        LEFT JOIN player_history ph ON p.id = ph.player_id
        WHERE proj.fpts IS NOT NULL
    """

    if position:
        query += f" AND p.positions LIKE '%{position}%'"

    query += " ORDER BY proj.fpts DESC"

    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_players_by_position(position: str) -> list[dict]:
    """Get players eligible at a specific position."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.id, p.name, p.mlb_team, p.positions, p.primary_position,
            proj.fpts, proj.ab, proj.hr, proj.rbi, proj.sb, proj.avg,
            proj.ip, proj.w, proj.sv, proj.k_pitch, proj.era,
            pb.pb_score, pb.true_value, pb.value_gap,
            pt.tier, pt.bid_floor, pt.bid_target, pt.bid_ceiling,
            ph.fpts_2023, ph.fpts_2024, ph.fpts_2025, ph.fpts_3ya
        FROM players p
        LEFT JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        LEFT JOIN pb_scores pb ON p.id = pb.player_id
        LEFT JOIN position_tiers pt ON p.id = pt.player_id AND pt.position = ?
        LEFT JOIN player_history ph ON p.id = ph.player_id
        WHERE p.positions LIKE ? AND proj.fpts IS NOT NULL
        ORDER BY proj.fpts DESC
    """, (position, f'%{position}%'))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_undrafted_players(position: Optional[str] = None) -> list[dict]:
    """Get players not yet drafted."""
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            p.id, p.name, p.mlb_team, p.positions, p.primary_position,
            proj.fpts, proj.ab, proj.hr, proj.rbi, proj.sb, proj.avg,
            proj.ip, proj.w, proj.sv, proj.k_pitch, proj.era,
            pb.pb_score, pb.true_value, pb.value_gap,
            pt.tier, pt.bid_floor, pt.bid_target, pt.bid_ceiling,
            ph.fpts_2023, ph.fpts_2024, ph.fpts_2025, ph.fpts_3ya
        FROM players p
        LEFT JOIN projections proj ON p.id = proj.player_id
            AND proj.season = 2026 AND proj.stat_type = 'projection'
        LEFT JOIN pb_scores pb ON p.id = pb.player_id
        LEFT JOIN position_tiers pt ON p.id = pt.player_id
            AND pt.position = p.primary_position
        LEFT JOIN player_history ph ON p.id = ph.player_id
        LEFT JOIN draft_picks dp ON p.id = dp.player_id
        WHERE dp.id IS NULL AND proj.fpts IS NOT NULL
    """

    if position:
        query += f" AND p.positions LIKE '%{position}%'"

    query += " ORDER BY pb.pb_score DESC NULLS LAST, proj.fpts DESC"

    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def record_draft_pick(player_id: int, team: str, salary: int, is_keeper: bool = False):
    """Record a draft pick."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM draft_picks")
    pick_order = cursor.fetchone()[0] + 1

    cursor.execute("""
        INSERT INTO draft_picks (player_id, team, salary, pick_order, is_keeper)
        VALUES (?, ?, ?, ?, ?)
    """, (player_id, team, salary, pick_order, is_keeper))

    cursor.execute("""
        UPDATE league_teams
        SET budget_remaining = budget_remaining - ?,
            players_drafted = players_drafted + 1
        WHERE name = ?
    """, (salary, team))

    conn.commit()
    conn.close()


def get_team_status() -> list[dict]:
    """Get all teams with their draft status."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name, budget_remaining, players_drafted, tendency
        FROM league_teams
        ORDER BY budget_remaining DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def init_league_teams(teams: dict):
    """Initialize league teams."""
    conn = get_connection()
    cursor = conn.cursor()

    for name, info in teams.items():
        cursor.execute("""
            INSERT OR REPLACE INTO league_teams (name, budget_remaining, tendency, notes)
            VALUES (?, 320, ?, ?)
        """, (name, info.get('style', ''), info.get('tendency', '')))

    conn.commit()
    conn.close()


def add_scouting_note(player_id: int, note: str, category: str = None, season: int = 2026):
    """Add a scouting note for a player."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO scouting_notes (player_id, note, category, season)
        VALUES (?, ?, ?, ?)
    """, (player_id, note, category, season))
    conn.commit()
    conn.close()


def get_scouting_notes(player_id: int) -> list[dict]:
    """Get all scouting notes for a player."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM scouting_notes
        WHERE player_id = ?
        ORDER BY created_at DESC
    """, (player_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_draft_history_for_player(player_name: str) -> list[dict]:
    """Get historical draft prices for a player."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT season, team, salary, fpts_total, fpts_active
        FROM draft_history
        WHERE player_name LIKE ?
        ORDER BY season DESC
    """, (f"%{player_name}%",))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_league_price(position: str, tier: int) -> dict:
    """Get average league price for position/tier combo."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM league_prices
        WHERE position = ? AND tier = ?
    """, (position, tier))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {'avg_salary': 1, 'dollars_per_fpts': 0.1}


if __name__ == "__main__":
    init_db()
    print("Database ready!")
