"""SQLite storage layer - append-only snapshots."""

import json
import logging
import sqlite3
from datetime import date, datetime, timedelta
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
    conn.commit()
    logger.info(f"Database initialized at {db_path}")
    return conn


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
         regulatory, wyckoff, rsi_daily, rsi_weekly, wyckoff_phase, action, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            asset["symbol"],
            snapshot_date,
            asset.get("composite"),
            scores.get("institutional"),
            scores.get("revenue"),
            scores.get("regulatory"),
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
    Get composite score trend for an asset.

    Args:
        conn: Database connection
        symbol: Asset symbol
        days: Number of days to fetch

    Returns:
        List of composite scores (oldest to newest)
    """
    cursor = conn.execute(
        """
        SELECT composite FROM snapshots
        WHERE asset_symbol = ? AND composite IS NOT NULL
        ORDER BY snapshot_date DESC
        LIMIT ?
        """,
        (symbol, days),
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
    Calculate days since last action change.

    Args:
        conn: Database connection
        symbol: Asset symbol

    Returns:
        Number of days since action changed
    """
    history = get_action_history(conn, symbol, 90)
    if len(history) < 2:
        return 0

    current_action = history[0]["action"]
    for i, entry in enumerate(history[1:], 1):
        if entry["action"] != current_action:
            return i

    return len(history) - 1


def get_strong_accumulate_days(conn: sqlite3.Connection, symbol: str) -> int:
    """
    Calculate consecutive days of strong-accumulate action.

    Args:
        conn: Database connection
        symbol: Asset symbol

    Returns:
        Number of consecutive days (0 if not currently strong-accumulate)
    """
    history = get_action_history(conn, symbol, 30)
    if not history or history[0]["action"] != "strong-accumulate":
        return 0

    count = 0
    for entry in history:
        if entry["action"] == "strong-accumulate":
            count += 1
        else:
            break

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
        (symbol, score_type, score, rationale, datetime.utcnow().isoformat()),
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
    cutoff = (datetime.utcnow() - timedelta(days=max_age_days)).isoformat()
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
