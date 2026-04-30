"""SQLite storage layer - append-only snapshots."""

import json
import logging
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_symbol TEXT NOT NULL,
    snapshot_date TEXT NOT NULL,
    composite INTEGER,
    institutional INTEGER,
    revenue INTEGER,
    regulatory INTEGER,
    supply INTEGER,
    wyckoff INTEGER,
    rsi_daily REAL,
    rsi_weekly REAL,
    wyckoff_phase TEXT,
    action TEXT,
    note TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asset_symbol, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_asset_date ON snapshots(asset_symbol, snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_date ON snapshots(snapshot_date DESC);
"""

WYCKOFF_STATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS wyckoff_state (
    asset_symbol TEXT PRIMARY KEY,
    wyckoff_phase TEXT,
    position_score INTEGER,
    updated_at TEXT NOT NULL
);
"""

QUALITATIVE_CACHE_SCHEMA = """
CREATE TABLE IF NOT EXISTS qualitative_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_symbol TEXT NOT NULL,
    score_type TEXT NOT NULL,
    score INTEGER,
    rationale TEXT,
    fetched_at TEXT NOT NULL,
    UNIQUE(asset_symbol, score_type)
);
"""


def init_db(db_path: Path) -> sqlite3.Connection:
    """
    Initialize database with schema.

    Args:
        db_path: Path to SQLite database file

    Returns:
        Database connection
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA busy_timeout = 60000')
    conn.executescript(SCHEMA)
    conn.executescript(WYCKOFF_STATE_SCHEMA)
    conn.executescript(QUALITATIVE_CACHE_SCHEMA)

    # Migration: add supply column if missing (for existing databases)
    _migrate_add_supply_column(conn)
    _migrate_add_wyckoff_state_table(conn)

    conn.commit()
    logger.info(f"Database initialized at {db_path}")
    return conn


def _migrate_add_wyckoff_state_table(conn: sqlite3.Connection) -> None:
    """Create wyckoff_state table if missing (daily indicators persist phase here)."""
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='wyckoff_state'"
    )
    if cur.fetchone() is None:
        logger.info("Migrating: creating wyckoff_state table")
        conn.executescript(WYCKOFF_STATE_SCHEMA)
        conn.commit()


def _migrate_add_supply_column(conn: sqlite3.Connection) -> None:
    """Add supply column to snapshots table if it doesn't exist."""
    cursor = conn.execute("PRAGMA table_info(snapshots)")
    columns = [row[1] for row in cursor.fetchall()]

    if "supply" not in columns:
        logger.info("Migrating: adding 'supply' column to snapshots table")
        conn.execute("ALTER TABLE snapshots ADD COLUMN supply INTEGER")
        conn.commit()


def save_snapshot(
    conn: sqlite3.Connection,
    asset: dict,
    snapshot_date: str,
    *,
    preserve_null_technicals: bool = False,
) -> None:
    """
    Save daily snapshot for an asset.

    Args:
        conn: Database connection
        asset: Asset data dict
        snapshot_date: ISO date string (YYYY-MM-DD)
        preserve_null_technicals: When True, RSI and action nulls are filled from the
            latest prior snapshot so dimension-only weekly runs do not erase technicals.
    """
    scores = asset.get("scores", {})
    rsi_d = asset.get("rsi_daily")
    rsi_w = asset.get("rsi_weekly")
    action = asset.get("action")
    if preserve_null_technicals and (rsi_d is None or rsi_w is None or action is None):
        prev = conn.execute(
            """
            SELECT rsi_daily, rsi_weekly, action FROM snapshots
            WHERE asset_symbol = ? AND snapshot_date < ?
            ORDER BY snapshot_date DESC
            LIMIT 1
            """,
            (asset["symbol"], snapshot_date),
        ).fetchone()
        if prev:
            if rsi_d is None:
                rsi_d = prev["rsi_daily"]
            if rsi_w is None:
                rsi_w = prev["rsi_weekly"]
            if action is None:
                action = prev["action"]
    conn.execute(
        """
        INSERT OR REPLACE INTO snapshots
        (asset_symbol, snapshot_date, composite, institutional, revenue,
         regulatory, supply, wyckoff, rsi_daily, rsi_weekly, wyckoff_phase, action, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            asset["symbol"],
            snapshot_date,
            asset.get("composite"),
            scores.get("institutional"),
            scores.get("value_capture", scores.get("revenue")),
            scores.get("regulatory"),
            scores.get("supply"),
            asset.get("wyckoff_position_score", scores.get("wyckoff")),
            rsi_d,
            rsi_w,
            asset.get("wyckoff_phase"),
            action,
            asset.get("note"),
        ),
    )


def get_trend_data(
    conn: sqlite3.Connection, symbol: str, days: int = 7
) -> list[int]:
    """
    Get composite score trend for an asset, excluding today's snapshot.

    Today is excluded because run.py always appends the freshly computed
    composite score to the returned list. If today's snapshot were included,
    re-running the pipeline on the same day would double-count today's value
    and shift the effective trend window.

    Args:
        conn: Database connection
        symbol: Asset symbol
        days: Number of days to fetch (excluding today)

    Returns:
        List of composite scores (oldest to newest)
    """
    today = date.today().isoformat()
    cursor = conn.execute(
        """
        SELECT composite FROM snapshots
        WHERE asset_symbol = ?
          AND composite IS NOT NULL
          AND snapshot_date < ?
        ORDER BY snapshot_date DESC
        LIMIT ?
        """,
        (symbol, today, days),
    )
    rows = cursor.fetchall()
    # Reverse to get oldest first
    return [row["composite"] for row in reversed(rows)]


def save_wyckoff_state(
    conn: sqlite3.Connection,
    symbol: str,
    phase: str,
    position_score: Optional[int],
) -> None:
    """Persist latest Wyckoff phase from daily indicators (not tied to snapshot rows)."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO wyckoff_state (asset_symbol, wyckoff_phase, position_score, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(asset_symbol) DO UPDATE SET
            wyckoff_phase = excluded.wyckoff_phase,
            position_score = excluded.position_score,
            updated_at = excluded.updated_at
        """,
        (symbol, phase, position_score, now),
    )


def get_last_wyckoff_phase(conn: sqlite3.Connection, symbol: str) -> Optional[str]:
    """
    Latest Wyckoff phase: prefer daily ``wyckoff_state``, else historical snapshots.

    Used by weekly dimension scoring so action logic can reference structure
    until the next daily indicators refresh.
    """
    row = conn.execute(
        """
        SELECT wyckoff_phase FROM wyckoff_state
        WHERE asset_symbol = ?
          AND wyckoff_phase IS NOT NULL
          AND TRIM(wyckoff_phase) != ''
        """,
        (symbol,),
    ).fetchone()
    if row and row["wyckoff_phase"]:
        return row["wyckoff_phase"]

    today = date.today().isoformat()
    cursor = conn.execute(
        """
        SELECT wyckoff_phase FROM snapshots
        WHERE asset_symbol = ?
          AND wyckoff_phase IS NOT NULL
          AND TRIM(wyckoff_phase) != ''
          AND snapshot_date < ?
        ORDER BY snapshot_date DESC
        LIMIT 1
        """,
        (symbol, today),
    )
    row2 = cursor.fetchone()
    return row2["wyckoff_phase"] if row2 else None


def get_composite_last_week(conn: sqlite3.Connection, symbol: str) -> Optional[int]:
    """
    Get composite score from 7 days ago.

    Args:
        conn: Database connection
        symbol: Asset symbol

    Returns:
        Composite score or None
    """
    target_date = (date.today() - timedelta(days=7)).isoformat()
    cursor = conn.execute(
        """
        SELECT composite FROM snapshots
        WHERE asset_symbol = ? AND snapshot_date <= ?
        ORDER BY snapshot_date DESC
        LIMIT 1
        """,
        (symbol, target_date),
    )
    row = cursor.fetchone()
    return row["composite"] if row else None


def get_weekly_composite_averages(
    conn: sqlite3.Connection, symbol: str, weeks: int = 10
) -> list[dict]:
    """
    Get weekly composite score averages for an asset.

    Groups multiple snapshots within the same ISO calendar week and averages them.
    This handles scenarios where scoring runs multiple times per week during calibration.

    Args:
        conn: Database connection
        symbol: Asset symbol
        weeks: Number of weeks to fetch (approximate - fetches enough days to cover this many weeks)

    Returns:
        List of {week_id, year, week, avg_composite, snapshot_count} dicts,
        sorted newest to oldest (by week). week_id format: "2026-W17"
    """
    # Fetch snapshots from the last N weeks (plus buffer for partial weeks)
    lookback_days = weeks * 7 + 14  # Add buffer for partial weeks
    cutoff_date = (date.today() - timedelta(days=lookback_days)).isoformat()

    cursor = conn.execute(
        """
        SELECT snapshot_date, composite FROM snapshots
        WHERE asset_symbol = ?
          AND composite IS NOT NULL
          AND snapshot_date >= ?
        ORDER BY snapshot_date ASC
        """,
        (symbol, cutoff_date),
    )

    rows = cursor.fetchall()
    if not rows:
        return []

    # Group by ISO calendar week (year, week_number)
    from collections import defaultdict
    weeks_data = defaultdict(list)

    for row in rows:
        snapshot_date = date.fromisoformat(row["snapshot_date"])
        iso_cal = snapshot_date.isocalendar()
        year, week_num = iso_cal.year, iso_cal.week
        week_id = f"{year}-W{week_num:02d}"
        weeks_data[week_id].append(row["composite"])

    # Calculate averages
    weekly_averages = []
    for week_id, composites in weeks_data.items():
        year, week = week_id.split('-W')
        weekly_averages.append({
            "week_id": week_id,
            "year": int(year),
            "week": int(week),
            "avg_composite": round(sum(composites) / len(composites), 1),
            "snapshot_count": len(composites),
        })

    # Sort by year and week (newest first)
    weekly_averages.sort(key=lambda x: (x["year"], x["week"]), reverse=True)

    return weekly_averages


def get_action_history(
    conn: sqlite3.Connection, symbol: str, days: int = 30
) -> list[dict]:
    """
    Get action state history for an asset.

    Args:
        conn: Database connection
        symbol: Asset symbol
        days: Number of days to fetch

    Returns:
        List of {date, action} dicts (newest first)
    """
    cursor = conn.execute(
        """
        SELECT snapshot_date, action FROM snapshots
        WHERE asset_symbol = ? AND action IS NOT NULL
        ORDER BY snapshot_date DESC
        LIMIT ?
        """,
        (symbol, days),
    )
    return [{"date": row["snapshot_date"], "action": row["action"]} for row in cursor]


def get_label_changed_days_ago(conn: sqlite3.Connection, symbol: str) -> int:
    """
    Calculate calendar days since the most recent action change.

    Excludes today so that repeated same-day pipeline runs don't flip the
    result depending on whether today's snapshot has already been saved.
    Uses real date deltas rather than row counts, so a gap in coverage (e.g.
    the pipeline was skipped for a few days) is reported as elapsed calendar
    time rather than a single row step.

    Args:
        conn: Database connection
        symbol: Asset symbol

    Returns:
        Number of calendar days since the action changed. Returns 0 when
        there is insufficient history to establish a previous action.
    """
    today = date.today()
    today_iso = today.isoformat()

    cursor = conn.execute(
        """
        SELECT snapshot_date, action FROM snapshots
        WHERE asset_symbol = ?
          AND action IS NOT NULL
          AND snapshot_date < ?
        ORDER BY snapshot_date DESC
        LIMIT 180
        """,
        (symbol, today_iso),
    )
    history = [
        (date.fromisoformat(row["snapshot_date"]), row["action"])
        for row in cursor
    ]

    if len(history) < 2:
        return 0

    current_action = history[0][1]
    for entry_date, entry_action in history[1:]:
        if entry_action != current_action:
            return (today - entry_date).days

    # No change found within the window — report span from oldest row.
    return (today - history[-1][0]).days


def get_strong_accumulate_days(conn: sqlite3.Connection, symbol: str) -> int:
    """
    Calculate consecutive weeks of strong-accumulate action BEFORE today.

    For a weekly pipeline (Sundays), this counts consecutive weekly snapshots
    in strong-accumulate state. Returns the count in days for backward compatibility
    (consecutive_weeks * 7).

    This excludes today's date to prevent double-counting when the pipeline
    is re-run on the same day (since run.py adds 1 if today is strong-accumulate).

    Args:
        conn: Database connection
        symbol: Asset symbol

    Returns:
        Number of days represented by consecutive weekly strong-accumulate snapshots (0 if none)
    """
    today = date.today().isoformat()

    # Get history excluding today's entry
    cursor = conn.execute(
        """
        SELECT snapshot_date, action FROM snapshots
        WHERE asset_symbol = ? AND action IS NOT NULL AND snapshot_date < ?
        ORDER BY snapshot_date DESC
        LIMIT 30
        """,
        (symbol, today),
    )
    history = [{"date": row["snapshot_date"], "action": row["action"]} for row in cursor]

    if not history:
        return 0

    # Count consecutive strong-accumulate snapshots (weekly pipeline runs on Sundays)
    # Accept snapshots that are 6-8 days apart to handle weekly runs with slight timing variance
    count = 0
    prev_date = None
    for entry in history:
        entry_date = date.fromisoformat(entry["date"])
        if entry["action"] != "strong-accumulate":
            break
        if prev_date is not None:
            days_gap = (prev_date - entry_date).days
            # Expect ~7 day gap for weekly pipeline; allow 6-8 days for timing variance
            if days_gap < 6 or days_gap > 8:
                break
        count += 1
        prev_date = entry_date

    # Return count in days (weeks * 7) for backward compatibility
    return count * 7


def get_history(
    conn: sqlite3.Connection, days: int = 90
) -> list[dict]:
    """
    Get full snapshot history for all assets.

    Args:
        conn: Database connection
        days: Number of days to fetch

    Returns:
        List of snapshot dicts
    """
    cutoff_date = (date.today() - timedelta(days=days)).isoformat()
    cursor = conn.execute(
        """
        SELECT * FROM snapshots
        WHERE snapshot_date >= ?
        ORDER BY snapshot_date DESC, asset_symbol
        """,
        (cutoff_date,),
    )
    return [dict(row) for row in cursor]


def save_qualitative_score(
    conn: sqlite3.Connection,
    symbol: str,
    score_type: str,
    score: int,
    rationale: str,
) -> None:
    """
    Cache qualitative score (regulatory/institutional).

    Args:
        conn: Database connection
        symbol: Asset symbol
        score_type: 'regulatory' or 'institutional'
        score: Score value
        rationale: Explanation text
    """
    conn.execute(
        """
        INSERT OR REPLACE INTO qualitative_cache
        (asset_symbol, score_type, score, rationale, fetched_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (symbol, score_type, score, rationale, datetime.now(timezone.utc).isoformat()),
    )


def get_cached_qualitative_score(
    conn: sqlite3.Connection,
    symbol: str,
    score_type: str,
    max_age_days: int = 7,
) -> Optional[dict]:
    """
    Get cached qualitative score if fresh enough.

    Args:
        conn: Database connection
        symbol: Asset symbol
        score_type: 'regulatory' or 'institutional'
        max_age_days: Maximum age in days before refreshing

    Returns:
        Dict with score and rationale, or None if stale/missing
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
    cursor = conn.execute(
        """
        SELECT score, rationale FROM qualitative_cache
        WHERE asset_symbol = ? AND score_type = ? AND fetched_at >= ?
        """,
        (symbol, score_type, cutoff),
    )
    row = cursor.fetchone()
    if row:
        return {"score": row["score"], "rationale": row["rationale"]}
    return None
