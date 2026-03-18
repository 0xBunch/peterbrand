"""Import CSV data into the database."""
import csv
import re
from pathlib import Path
from typing import Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.database import get_connection, init_db, get_player_id


DATA_DIR = Path(__file__).parent.parent / "01_mlb"
PROJECTIONS_DIR = DATA_DIR / "projections_2026"
STATS_2025_DIR = DATA_DIR / "stats_2025"
STATS_3YA_DIR = DATA_DIR / "stats_23-25-3ya"
DRAFT_HISTORY_DIR = Path(__file__).parent.parent / "02_league" / "draft_history"


def parse_player_info(player_str: str) -> tuple[str, list[str], str]:
    """Parse player string like 'Aaron Judge OF | NYY' into (name, positions, team)."""
    # Remove leading/trailing whitespace
    player_str = player_str.strip()

    # Split by pipe to separate team
    if "|" in player_str:
        name_pos, team = player_str.rsplit("|", 1)
        team = team.strip()
    else:
        name_pos = player_str
        team = "FA"

    name_pos = name_pos.strip()

    # Find positions (uppercase letters at end, possibly comma-separated)
    # Pattern: name followed by position codes
    position_pattern = r'\s+((?:C|1B|2B|3B|SS|OF|DH|SP|RP)(?:,(?:C|1B|2B|3B|SS|OF|DH|SP|RP))*)\s*$'
    match = re.search(position_pattern, name_pos)

    if match:
        positions_str = match.group(1)
        name = name_pos[:match.start()].strip()
        positions = [p.strip() for p in positions_str.split(',')]
    else:
        # Fallback: assume last word(s) are positions
        parts = name_pos.split()
        positions = []
        name_parts = []
        for part in parts:
            if part in ['C', '1B', '2B', '3B', 'SS', 'OF', 'DH', 'SP', 'RP']:
                positions.append(part)
            elif ',' in part:
                # Could be comma-separated positions
                sub_parts = part.split(',')
                if all(p in ['C', '1B', '2B', '3B', 'SS', 'OF', 'DH', 'SP', 'RP'] for p in sub_parts):
                    positions.extend(sub_parts)
                else:
                    name_parts.append(part)
            else:
                name_parts.append(part)
        name = ' '.join(name_parts)

    return name, positions, team


def safe_float(val: str) -> Optional[float]:
    """Convert string to float, handling empty strings."""
    if not val or val.strip() == '':
        return None
    try:
        return float(val.strip())
    except ValueError:
        return None


def safe_int(val: str) -> Optional[int]:
    """Convert string to int, handling empty strings."""
    f = safe_float(val)
    return int(f) if f is not None else None


def import_hitter_projections(filepath: Path, season: int, stat_type: str, position_hint: str):
    """Import hitter projection CSV."""
    conn = get_connection()
    cursor = conn.cursor()

    with open(filepath, 'r') as f:
        # Skip header line
        next(f)
        reader = csv.DictReader(f)

        for row in reader:
            player_str = row.get('Player', '')
            if not player_str or player_str.strip() == '':
                continue

            name, positions, team = parse_player_info(player_str)

            # If no positions found, use the hint from filename
            if not positions:
                positions = [position_hint]

            # Get or create player
            player_id = get_player_id(name, team, conn)

            # Update player positions
            positions_str = ','.join(positions)
            primary_pos = positions[0] if positions else position_hint
            cursor.execute("""
                UPDATE players SET positions = ?, primary_position = ?
                WHERE id = ?
            """, (positions_str, primary_pos, player_id))

            # Insert projection
            cursor.execute("""
                INSERT OR REPLACE INTO projections (
                    player_id, season, stat_type,
                    ab, r, h, singles, doubles, triples,
                    hr, rbi, bb, k, sb, cs, avg, obp, slg, fpts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                player_id, season, stat_type,
                safe_int(row.get('AB', '')),
                safe_int(row.get('R', '')),
                safe_int(row.get('H', '')),
                safe_int(row.get('1B', '')),
                safe_int(row.get('2B', '')),
                safe_int(row.get('3B', '')),
                safe_int(row.get('HR', '')),
                safe_int(row.get('RBI', '')),
                safe_int(row.get('BB', '')),
                safe_int(row.get('K', '')),
                safe_int(row.get('SB', '')),
                safe_int(row.get('CS', '')),
                safe_float(row.get('AVG', '')),
                safe_float(row.get('OBP', '')),
                safe_float(row.get('SLG', '')),
                safe_float(row.get('FPTS', ''))
            ))

    conn.commit()
    conn.close()


def import_pitcher_projections(filepath: Path, season: int, stat_type: str, position_hint: str):
    """Import pitcher projection CSV."""
    conn = get_connection()
    cursor = conn.cursor()

    with open(filepath, 'r') as f:
        # Skip header line
        next(f)
        reader = csv.DictReader(f)

        for row in reader:
            player_str = row.get('Player', '')
            if not player_str or player_str.strip() == '':
                continue

            name, positions, team = parse_player_info(player_str)

            if not positions:
                positions = [position_hint]

            player_id = get_player_id(name, team, conn)

            positions_str = ','.join(positions)
            primary_pos = positions[0] if positions else position_hint
            cursor.execute("""
                UPDATE players SET positions = ?, primary_position = ?
                WHERE id = ?
            """, (positions_str, primary_pos, player_id))

            cursor.execute("""
                INSERT OR REPLACE INTO projections (
                    player_id, season, stat_type,
                    ip, app, gs, qs, cg, w, l, sv, bs, hd,
                    k_pitch, bb_pitch, h_pitch, era, whip, fpts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                player_id, season, stat_type,
                safe_float(row.get('INNs', '')),
                safe_int(row.get('APP', '')),
                safe_int(row.get('GS', '')),
                safe_int(row.get('QS', '')),
                safe_int(row.get('CG', '')),
                safe_int(row.get('W', '')),
                safe_int(row.get('L', '')),
                safe_int(row.get('S', '')),
                safe_int(row.get('BS', '')),
                safe_int(row.get('HD', '')),
                safe_int(row.get('K', '')),
                safe_int(row.get('BB', '')),
                safe_int(row.get('H', '')),
                safe_float(row.get('ERA', '')),
                safe_float(row.get('WHIP', '')),
                safe_float(row.get('FPTS', ''))
            ))

    conn.commit()
    conn.close()


def import_draft_history(filepath: Path, season: int):
    """Import draft history CSV."""
    conn = get_connection()
    cursor = conn.cursor()

    with open(filepath, 'r') as f:
        lines = f.readlines()

    current_team = None
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Check if this is a team name line (no commas, or starts with a team name)
        if line and not line.startswith('Pos,'):
            # Could be team name
            if ',' not in line or (line.count(',') <= 1 and not any(c.isdigit() for c in line)):
                current_team = line.rstrip(',')
                i += 1
                continue

        # Skip header
        if line.startswith('Pos,'):
            i += 1
            continue

        if not line or not current_team:
            i += 1
            continue

        # Parse player line
        try:
            reader = csv.reader([line])
            row = next(reader)
            if len(row) >= 4:
                pos = row[0]
                player_str = row[1]
                salary = safe_int(row[2])

                # Parse fpts
                fpts_total = safe_float(row[4]) if len(row) > 4 else None
                fpts_active = safe_float(row[5]) if len(row) > 5 else None

                if player_str and salary:
                    name, positions, team = parse_player_info(player_str)
                    cursor.execute("""
                        INSERT INTO draft_history (
                            season, player_name, team, position, salary, fpts_total, fpts_active
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (season, name, current_team, pos, salary, fpts_total, fpts_active))
        except Exception as e:
            print(f"Error parsing line: {line} - {e}")

        i += 1

    conn.commit()
    conn.close()


def import_3ya_stats(filepath: Path, position_hint: str, is_pitcher: bool = False):
    """Import 3-year average stats and populate player_history."""
    conn = get_connection()
    cursor = conn.cursor()

    with open(filepath, 'r') as f:
        next(f)  # Skip header
        reader = csv.DictReader(f)

        for row in reader:
            player_str = row.get('Player', '')
            if not player_str or player_str.strip() == '':
                continue

            name, positions, team = parse_player_info(player_str)
            if not positions:
                positions = [position_hint]

            player_id = get_player_id(name, team, conn)
            fpts_3ya = safe_float(row.get('FPTS', ''))

            # Store 3YA in player_history
            cursor.execute("""
                INSERT OR REPLACE INTO player_history (player_id, fpts_3ya)
                VALUES (?, ?)
            """, (player_id, fpts_3ya))

            # Store current owner info in opponent_rosters if not waiver
            avail = row.get('Avail', 'W').strip()
            if avail and avail != 'W':
                cursor.execute("""
                    INSERT OR REPLACE INTO opponent_rosters
                    (team, player_id, season, position_slot)
                    VALUES (?, ?, 2025, ?)
                """, (avail, player_id, position_hint))

    conn.commit()
    conn.close()


def link_draft_history_to_players():
    """Link draft history records to player IDs for calibration."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, player_name FROM draft_history WHERE player_id IS NULL")
    records = cursor.fetchall()

    for record_id, player_name in records:
        cursor.execute("SELECT id FROM players WHERE name LIKE ?", (f"%{player_name}%",))
        match = cursor.fetchone()
        if match:
            cursor.execute("UPDATE draft_history SET player_id = ? WHERE id = ?", (match[0], record_id))

    conn.commit()
    conn.close()


def import_all_data():
    """Import all available data."""
    print("Initializing database...")
    init_db()

    hitter_positions = ['c', '1b', '2b', '3b', 'ss', 'of', 'dh']
    pitcher_positions = ['sp', 'rp']

    # Import 2026 projections
    print("\nImporting 2026 projections...")
    for pos in hitter_positions:
        filepath = PROJECTIONS_DIR / f"projections_{pos}_2026.csv"
        if filepath.exists():
            print(f"  Importing {pos.upper()} projections...")
            import_hitter_projections(filepath, 2026, 'projection', pos.upper())

    for pos in pitcher_positions:
        filepath = PROJECTIONS_DIR / f"projections_{pos}_2026.csv"
        if filepath.exists():
            print(f"  Importing {pos.upper()} projections...")
            import_pitcher_projections(filepath, 2026, 'projection', pos.upper())

    # Import 2025 stats
    print("\nImporting 2025 stats...")
    for pos in hitter_positions:
        filepath = STATS_2025_DIR / f"stats_{pos}_2025.csv"
        if filepath.exists():
            print(f"  Importing {pos.upper()} 2025 stats...")
            import_hitter_projections(filepath, 2025, 'actual', pos.upper())

    for pos in pitcher_positions:
        filepath = STATS_2025_DIR / f"stats_{pos}_2025.csv"
        if filepath.exists():
            print(f"  Importing {pos.upper()} 2025 stats...")
            import_pitcher_projections(filepath, 2025, 'actual', pos.upper())

    # Import 3-year average stats
    print("\nImporting 3-year average stats...")
    for pos in hitter_positions:
        filepath = STATS_3YA_DIR / f"stats_{pos}_23-25.csv"
        if filepath.exists():
            print(f"  Importing {pos.upper()} 3YA stats...")
            import_3ya_stats(filepath, pos.upper(), is_pitcher=False)

    for pos in pitcher_positions:
        filepath = STATS_3YA_DIR / f"stats_{pos}_23-25.csv"
        if filepath.exists():
            print(f"  Importing {pos.upper()} 3YA stats...")
            import_3ya_stats(filepath, pos.upper(), is_pitcher=True)

    # Import draft history
    print("\nImporting draft history...")
    for year in [2021, 2022, 2023, 2024, 2025]:
        filepath = DRAFT_HISTORY_DIR / f"{year}_draft.csv"
        if filepath.exists():
            print(f"  Importing {year} draft...")
            import_draft_history(filepath, year)

    # Link draft history to player IDs
    print("\nLinking draft history to players...")
    link_draft_history_to_players()

    # Count imported data
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM players")
    player_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM projections WHERE season = 2026")
    proj_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM draft_history")
    draft_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM player_history WHERE fpts_3ya IS NOT NULL")
    history_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM opponent_rosters")
    roster_count = cursor.fetchone()[0]
    conn.close()

    print(f"\nImport complete!")
    print(f"  Players: {player_count}")
    print(f"  2026 Projections: {proj_count}")
    print(f"  Draft History Records: {draft_count}")
    print(f"  Players with 3YA History: {history_count}")
    print(f"  Opponent Roster Records: {roster_count}")


if __name__ == "__main__":
    import_all_data()
