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
    conn.executescript(SCHEMA)
    conn.executescript(QUALITATIVE_CACHE_SCHEMA)

    # Migration: add supply column if missing (for existing databases)
    _migrate_add_supply_column(conn)

    conn.commit()
    logger.info(f"Database initialized at {db_path}")
    return conn


def _migrate_add_supply_column(conn: sqlite3.Connection) -> None:
    """Add supply column to snapshots table if it doesn't exist."""
    cursor = conn.execute("PRAGMA table_info(snapshots)")
    columns = [row[1] for row in cursor.fetchall()]

    if "supply" not in columns:
        logger.info("Migrating: adding 'supply' column to snapshots table")
        conn.execute("ALTER TABLE snapshots ADD COLUMN supply INTEGER")
        conn.commit()


def save_snapshot(conn: sqlite3.Connection, asset: dict, snapshot_date: str) -> None:
    """
    Save daily snapshot for an asset.

    Args:
        conn: Database connection
        asset: Asset data dict
        snapshot_date: ISO date string (YYYY-MM-DD)
    """
    scores = asset.get("scores", {})
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
            scores.get("revenue"),
            scores.get("regulatory"),
            scores.get("supply"),
            scores.get("wyckoff"),
            asset.get("rsi_daily"),
            asset.get("rsi_weekly"),
            asset.get("wyckoff_phase"),
            asset.get("action"),
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
    Calculate consecutive days of strong-accumulate action BEFORE today.

    This excludes today's date to prevent double-counting when the pipeline
    is re-run on the same day (since run.py adds 1 if today is strong-accumulate).

    Args:
        conn: Database connection
        symbol: Asset symbol

    Returns:
        Number of consecutive days before today (0 if none)
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

    # Count consecutive strong-accumulate days before today, requiring the
    # snapshot dates to be calendar-adjacent. A gap (e.g. pipeline skipped a
    # day) should reset the streak rather than silently extend it.
    count = 0
    expected_date = date.today() - timedelta(days=1)
    for entry in history:
        entry_date = date.fromisoformat(entry["date"])
        if entry["action"] != "strong-accumulate":
            break
        if entry_date != expected_date:
            break
        count += 1
        expected_date = entry_date - timedelta(days=1)

    return count


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
