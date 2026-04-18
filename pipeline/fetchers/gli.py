"""Global Liquidity Index (GLI) fetcher.

The GLI is a macro indicator tracking global central bank liquidity.
When GLI is in a downtrend (today < N days ago), it signals liquidity contraction
which historically suppresses crypto rallies.

Data sources (in priority order):
1. Manual override via environment variable or config
2. TradingView chart data (ECONOMICS:GLI)
3. Fallback: neutral (filter disabled)

Usage:
    from pipeline.fetchers import gli

    gli_data = gli.fetch_gli_data(offset_days=75)
    if gli_data['downtrend']:
        # Suppress strong signals
"""

import logging
import os
import time
from datetime import date, datetime, timedelta
from typing import Optional, TypedDict

import requests

from pipeline.config import config

logger = logging.getLogger(__name__)


class GLIData(TypedDict):
    """GLI data structure."""
    current: Optional[float]      # Current GLI value
    offset_value: Optional[float] # GLI value N days ago
    offset_days: int              # N days offset used
    downtrend: bool               # True if current < offset (liquidity contracting)
    source: str                   # Data source used
    fetched_at: str               # ISO timestamp


# Cache to avoid repeated fetches
_gli_cache: Optional[GLIData] = None
_gli_cache_time: float = 0
CACHE_TTL_SECONDS = 3600  # 1 hour


def fetch_gli_data(offset_days: Optional[int] = None) -> GLIData:
    """
    Fetch Global Liquidity Index data and determine trend.

    Args:
        offset_days: Days to look back for comparison (default from config)

    Returns:
        GLIData with current value, offset value, and downtrend flag
    """
    global _gli_cache, _gli_cache_time

    # Check cache
    if _gli_cache and (time.time() - _gli_cache_time) < CACHE_TTL_SECONDS:
        return _gli_cache

    gli_cfg = config.gli
    if offset_days is None:
        offset_days = gli_cfg.offset_days

    # Try data sources in order
    data = _try_manual_override(offset_days)
    if data:
        _gli_cache = data
        _gli_cache_time = time.time()
        return data

    data = _try_tradingview(offset_days)
    if data:
        _gli_cache = data
        _gli_cache_time = time.time()
        return data

    data = _try_fred_m2(offset_days)
    if data:
        _gli_cache = data
        _gli_cache_time = time.time()
        return data

    # Fallback: neutral (no filter applied)
    logger.warning("GLI data unavailable - filter disabled")
    data = GLIData(
        current=None,
        offset_value=None,
        offset_days=offset_days,
        downtrend=False,  # Neutral = don't suppress signals
        source="fallback",
        fetched_at=datetime.utcnow().isoformat(),
    )
    _gli_cache = data
    _gli_cache_time = time.time()
    return data


def _try_manual_override(offset_days: int) -> Optional[GLIData]:
    """
    Check for manual GLI override via environment variables.

    Set GLI_CURRENT and GLI_OFFSET to manually specify values.
    """
    gli_current = os.environ.get("GLI_CURRENT")
    gli_offset = os.environ.get("GLI_OFFSET")

    if gli_current and gli_offset:
        try:
            current = float(gli_current)
            offset_val = float(gli_offset)
            logger.info(f"GLI manual override: current={current}, offset={offset_val}")
            return GLIData(
                current=current,
                offset_value=offset_val,
                offset_days=offset_days,
                downtrend=current < offset_val,
                source="manual_override",
                fetched_at=datetime.utcnow().isoformat(),
            )
        except ValueError:
            logger.warning("Invalid GLI manual override values")

    return None


def _try_tradingview(offset_days: int) -> Optional[GLIData]:
    """
    Fetch GLI data from TradingView's charting endpoints.

    TradingView doesn't have an official API, but their chart data
    is accessible via their internal endpoints.
    """
    try:
        # TradingView uses a symbol format like "ECONOMICS:GLI" or similar
        # Their chart data API is at tradingview.com/chart-data/
        # This is an informal endpoint that may change

        symbol = config.gli.tradingview_symbol

        # Try TradingView's scanner endpoint for economic data
        # Note: This is not an official API and may require updates
        url = "https://scanner.tradingview.com/global/scan"

        payload = {
            "symbols": {"tickers": [symbol]},
            "columns": ["close", "change"]
        }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            if data.get("data") and len(data["data"]) > 0:
                row = data["data"][0]
                if row.get("d"):
                    current = row["d"][0]  # close price
                    # For historical data, we'd need a different approach
                    # TradingView requires authentication for historical data
                    logger.info(f"GLI from TradingView: current={current}")
                    # Can't get historical without auth, so fallback

        # Alternative: Try to get from TradingView's public chart API
        # This requires more complex session handling
        logger.debug("TradingView GLI fetch attempted but historical data requires auth")
        return None

    except Exception as e:
        logger.debug(f"TradingView GLI fetch failed: {e}")
        return None


def _try_fred_m2(offset_days: int) -> Optional[GLIData]:
    """
    Fallback: Use FRED M2 money supply as a proxy for global liquidity.

    This is US-only but correlates with global liquidity trends.
    Requires FRED_API_KEY environment variable.
    """
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        return None

    try:
        # FRED series: M2SL (M2 Money Stock)
        end_date = date.today()
        start_date = end_date - timedelta(days=offset_days + 30)  # Extra buffer

        url = (
            f"https://api.stlouisfed.org/fred/series/observations"
            f"?series_id=M2SL"
            f"&api_key={api_key}"
            f"&file_type=json"
            f"&observation_start={start_date.isoformat()}"
            f"&observation_end={end_date.isoformat()}"
        )

        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return None

        data = resp.json()
        observations = data.get("observations", [])

        if len(observations) < 2:
            return None

        # Get most recent value
        current_val = None
        for obs in reversed(observations):
            if obs["value"] != ".":
                current_val = float(obs["value"])
                break

        # Get value from ~offset_days ago
        offset_date = end_date - timedelta(days=offset_days)
        offset_val = None
        for obs in observations:
            obs_date = datetime.strptime(obs["date"], "%Y-%m-%d").date()
            if obs_date <= offset_date and obs["value"] != ".":
                offset_val = float(obs["value"])

        if current_val and offset_val:
            logger.info(f"GLI (M2 proxy) from FRED: current={current_val}, offset={offset_val}")
            return GLIData(
                current=current_val,
                offset_value=offset_val,
                offset_days=offset_days,
                downtrend=current_val < offset_val,
                source="fred_m2",
                fetched_at=datetime.utcnow().isoformat(),
            )

    except Exception as e:
        logger.debug(f"FRED M2 fetch failed: {e}")

    return None


def is_gli_downtrend() -> bool:
    """
    Simple helper to check if GLI is in downtrend.

    Returns:
        True if global liquidity is contracting, False otherwise
    """
    if not config.gli.enabled:
        return False

    data = fetch_gli_data()
    return data["downtrend"]


def get_gli_status() -> dict:
    """
    Get GLI status for dashboard display.

    Returns:
        Dict with trend, values, and human-readable status
    """
    data = fetch_gli_data()

    if data["current"] is None:
        return {
            "available": False,
            "message": "GLI data unavailable",
        }

    pct_change = ((data["current"] - data["offset_value"]) / data["offset_value"] * 100
                  if data["offset_value"] else 0)

    return {
        "available": True,
        "current": data["current"],
        "offset_value": data["offset_value"],
        "offset_days": data["offset_days"],
        "downtrend": data["downtrend"],
        "pct_change": round(pct_change, 2),
        "message": (
            f"GLI {'contracting' if data['downtrend'] else 'expanding'} "
            f"({pct_change:+.1f}% vs {data['offset_days']}d ago)"
        ),
        "source": data["source"],
    }
