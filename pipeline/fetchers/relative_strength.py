"""Relative Strength (RS) vs BTC calculation.

Compares each asset's performance against Bitcoin to detect assets
that are underperforming the market leader. When an asset is in a
prolonged downtrend relative to BTC, accumulation signals are muted.
"""

import logging
from typing import Optional

from pipeline.config import config
from pipeline.fetchers import defillama

logger = logging.getLogger(__name__)

# Cache BTC prices for the session (fetched once, reused for all assets)
_btc_prices_cache: Optional[list[tuple[int, float]]] = None


def _get_btc_prices() -> Optional[list[tuple[int, float]]]:
    """Fetch and cache BTC prices for RS calculation."""
    global _btc_prices_cache
    if _btc_prices_cache is None:
        _btc_prices_cache = defillama.fetch_daily_prices_with_timestamps(
            "bitcoin", days=config.data.price_history_days
        )
    return _btc_prices_cache


def compute_relative_strength(
    asset_prices: Optional[list[tuple[int, float]]],
    symbol: str,
) -> dict:
    """
    Compute relative strength of an asset vs BTC.

    RS = asset_price / btc_price
    If RS today < RS N days ago by more than threshold, asset is underperforming.

    Args:
        asset_prices: List of (timestamp, price) tuples for the asset
        symbol: Asset symbol (for logging)

    Returns:
        Dict with:
        - underperforming: bool - True if asset is underperforming BTC
        - rs_change_pct: float - Percentage change in RS ratio over lookback
        - current_rs: float - Current RS ratio (asset/BTC)
        - lookback_rs: float - RS ratio from lookback_days ago
    """
    rs_cfg = config.rs
    result = {
        "underperforming": False,
        "rs_change_pct": None,
        "current_rs": None,
        "lookback_rs": None,
    }

    # Skip if RS filter is disabled
    if not rs_cfg.enabled:
        return result

    # Skip BTC (RS vs itself is always 1.0)
    if symbol.upper() == "BTC":
        result["current_rs"] = 1.0
        result["lookback_rs"] = 1.0
        result["rs_change_pct"] = 0.0
        return result

    # Need both asset and BTC prices
    if not asset_prices:
        logger.debug(f"No price data for {symbol}, skipping RS calculation")
        return result

    btc_prices = _get_btc_prices()
    if not btc_prices:
        logger.debug("No BTC price data, skipping RS calculation")
        return result

    # Convert timestamps to dates for matching (DefiLlama timestamps vary slightly)
    from datetime import datetime, timezone

    def ts_to_date(ts):
        return datetime.fromtimestamp(ts, tz=timezone.utc).date()

    # Build date-based maps (use last price of each date)
    btc_by_date = {}
    for ts, price in btc_prices:
        d = ts_to_date(ts)
        btc_by_date[d] = price

    asset_by_date = {}
    for ts, price in asset_prices:
        d = ts_to_date(ts)
        asset_by_date[d] = price

    # Get dates that exist in both
    common_dates = sorted(set(btc_by_date.keys()) & set(asset_by_date.keys()))
    if len(common_dates) < rs_cfg.lookback_days:
        logger.debug(f"Insufficient overlapping data for {symbol} RS calculation ({len(common_dates)} days)")
        return result

    # Calculate RS at current and lookback points
    current_date = common_dates[-1]
    lookback_date = common_dates[-rs_cfg.lookback_days]

    current_asset = asset_by_date[current_date]
    current_btc = btc_by_date[current_date]
    lookback_asset = asset_by_date[lookback_date]
    lookback_btc = btc_by_date[lookback_date]

    if current_btc == 0 or lookback_btc == 0:
        return result

    current_rs = current_asset / current_btc
    lookback_rs = lookback_asset / lookback_btc

    if lookback_rs == 0:
        return result

    # Calculate percentage change in RS
    rs_change_pct = (current_rs - lookback_rs) / lookback_rs

    result["current_rs"] = current_rs
    result["lookback_rs"] = lookback_rs
    result["rs_change_pct"] = rs_change_pct

    # Check if underperforming by threshold
    if rs_change_pct <= -rs_cfg.underperformance_threshold:
        result["underperforming"] = True
        logger.debug(
            f"{symbol} underperforming BTC: RS changed {rs_change_pct*100:.1f}% "
            f"over {rs_cfg.lookback_days} days (threshold: -{rs_cfg.underperformance_threshold*100}%)"
        )

    return result


def clear_cache():
    """Clear the BTC price cache (call at start of each pipeline run)."""
    global _btc_prices_cache
    _btc_prices_cache = None
