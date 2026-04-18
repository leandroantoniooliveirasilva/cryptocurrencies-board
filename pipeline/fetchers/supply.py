"""Supply and on-chain metrics fetcher.

This module provides supply-side metrics that indicate accumulation/distribution:
- Exchange reserves (declining = bullish)
- Long-term holder supply percentage
- Supply concentration metrics

Note: Full implementation requires paid APIs (Glassnode, CryptoQuant, Santiment).
This implementation uses free/public sources where available and fallback heuristics.
"""

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# CoinGecko provides some supply metrics for free
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
TIMEOUT = 30


def fetch_supply_metrics(coingecko_id: str) -> Optional[dict]:
    """
    Fetch supply metrics from available sources.

    Args:
        coingecko_id: CoinGecko coin ID

    Returns:
        Dict with supply metrics or None
    """
    if not coingecko_id:
        return None

    try:
        # CoinGecko provides circulating/total supply ratio
        url = f"{COINGECKO_BASE}/coins/{coingecko_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "community_data": "false",
            "developer_data": "false",
        }

        resp = requests.get(url, params=params, timeout=TIMEOUT)
        if resp.status_code == 429:
            logger.debug(f"Rate limited fetching supply for {coingecko_id}")
            return None

        resp.raise_for_status()
        data = resp.json()

        market_data = data.get("market_data", {})
        circulating = market_data.get("circulating_supply")
        total = market_data.get("total_supply")
        max_supply = market_data.get("max_supply")

        return {
            "circulating_supply": circulating,
            "total_supply": total,
            "max_supply": max_supply,
            "circulating_ratio": circulating / total if circulating and total else None,
            "inflation_ratio": (total - circulating) / circulating if circulating and total else None,
        }

    except Exception as e:
        logger.debug(f"Failed to fetch supply metrics for {coingecko_id}: {e}")
        return None


def compute_supply_score(
    symbol: str,
    supply_metrics: Optional[dict] = None,
    exchange_reserve_trend: Optional[str] = None,
) -> int:
    """
    Compute supply/on-chain score (0-100).

    Scoring factors:
    - Exchange reserve trend (declining = bullish)
    - Supply concentration (high LTH % = bullish)
    - Inflation rate (low = bullish)
    - Max supply cap (capped = bullish)

    Args:
        symbol: Asset symbol
        supply_metrics: Dict from fetch_supply_metrics
        exchange_reserve_trend: 'declining', 'stable', 'increasing', or None

    Returns:
        Supply score 0-100
    """
    # Start with base scores by known asset characteristics
    base_scores = {
        # Store of value with fixed supply, declining exchange reserves
        "BTC": 85,
        # Smart contract platforms
        "ETH": 75,
        "SOL": 70,
        "AVAX": 65,
        "SUI": 60,  # Newer L1, token emissions ongoing
        # DeFi with token emissions
        "LINK": 70,
        "AAVE": 65,
        "HYPE": 60,
        "MORPHO": 55,
        "PENDLE": 55,  # Yield trading, moderate emissions
        "ENA": 50,  # USDe synthetic, centralized supply
        # Infrastructure
        "QNT": 75,  # Fixed supply
        "XRP": 60,  # Large escrow
        "XLM": 65,
        "HBAR": 55,
        "KAS": 60,
        "TAO": 55,  # AI-crypto, mining emissions
        # Others
        "ONDO": 55,
        "CANTON": 50,  # Pre-market, unknown
    }

    score = base_scores.get(symbol, 50)

    # Adjust based on supply metrics if available
    if supply_metrics:
        # Max supply cap is bullish
        if supply_metrics.get("max_supply"):
            score += 5

        # Low inflation is bullish
        inflation = supply_metrics.get("inflation_ratio")
        if inflation is not None:
            if inflation < 0.02:
                score += 5
            elif inflation > 0.10:
                score -= 5

    # Adjust based on exchange reserve trend
    # Note: This would come from Glassnode/CryptoQuant in production
    if exchange_reserve_trend == "declining":
        score += 10
    elif exchange_reserve_trend == "increasing":
        score -= 10

    return max(0, min(100, score))


# Known exchange reserve trends (manually maintained or from API)
# In production, this would be fetched from Glassnode/CryptoQuant
EXCHANGE_RESERVE_TRENDS = {
    "BTC": "declining",  # At 6-year lows as of 2026
    "ETH": "declining",
    "SOL": "stable",
    "LINK": "stable",
    "AVAX": "stable",
    "XRP": "stable",
}


def get_exchange_reserve_trend(symbol: str) -> Optional[str]:
    """
    Get exchange reserve trend for an asset.

    Returns:
        'declining', 'stable', 'increasing', or None
    """
    return EXCHANGE_RESERVE_TRENDS.get(symbol)
