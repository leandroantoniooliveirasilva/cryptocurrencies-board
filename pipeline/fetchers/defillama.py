"""DefiLlama API fetcher for TVL, fees, revenue, and price data."""

import logging
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://api.llama.fi"
COINS_URL = "https://coins.llama.fi"
TIMEOUT = 30
REQUEST_DELAY = 1.0  # seconds between requests to be respectful


def fetch_defillama_data(slug: str) -> Optional[dict]:
    """
    Fetch protocol data from DefiLlama.

    Args:
        slug: DefiLlama protocol slug (e.g., 'solana', 'aave')

    Returns:
        Dict with 'tvl', 'fees_24h', 'revenue_24h' or None on failure
    """
    if not slug:
        return None

    try:
        # Fetch TVL
        tvl_data = _fetch_tvl(slug)

        # Fetch fees/revenue
        fees_data = _fetch_fees(slug)

        return {
            "tvl": tvl_data.get("tvl") if tvl_data else None,
            "fees_24h": fees_data.get("total24h") if fees_data else None,
            "revenue_24h": fees_data.get("dailyRevenue") if fees_data else None,
        }

    except Exception as e:
        logger.warning(f"Failed to fetch DefiLlama data for {slug}: {e}")
        return None


def _fetch_tvl(slug: str) -> Optional[dict]:
    """Fetch TVL data for a protocol."""
    time.sleep(REQUEST_DELAY)
    try:
        resp = requests.get(f"{BASE_URL}/protocol/{slug}", timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return {"tvl": data.get("currentChainTvls", {}).get("total", data.get("tvl"))}
    except Exception as e:
        logger.debug(f"TVL fetch failed for {slug}: {e}")
        return None


def _fetch_fees(slug: str) -> Optional[dict]:
    """Fetch fees and revenue data for a protocol."""
    time.sleep(REQUEST_DELAY)
    try:
        resp = requests.get(f"{BASE_URL}/summary/fees/{slug}", timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.debug(f"Fees fetch failed for {slug}: {e}")
        return None


def fetch_daily_prices(coingecko_id: str, days: int = 120) -> Optional[list[float]]:
    """
    Fetch daily closing prices from DefiLlama coins API.

    Uses coingecko:{id} format which DefiLlama supports.

    Args:
        coingecko_id: CoinGecko coin ID (e.g., 'bitcoin', 'solana')
        days: Number of days of history

    Returns:
        List of daily closing prices (oldest to newest) or None
    """
    if not coingecko_id:
        return None

    time.sleep(REQUEST_DELAY)

    try:
        # DefiLlama accepts coingecko IDs with prefix
        coin = f"coingecko:{coingecko_id}"

        # Calculate timestamps
        end_ts = int(time.time())
        start_ts = end_ts - (days * 24 * 60 * 60)

        # Use the chart endpoint for historical data
        url = f"{COINS_URL}/chart/{coin}"
        params = {"start": start_ts, "span": days, "period": "1d"}

        resp = requests.get(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        # Extract prices from coins data
        coins_data = data.get("coins", {}).get(coin, {})
        prices_data = coins_data.get("prices", [])

        if not prices_data:
            logger.warning(f"No price data returned from DefiLlama for {coingecko_id}")
            return None

        # prices_data is [{"timestamp": ts, "price": price}, ...]
        prices = [p["price"] for p in prices_data if "price" in p]
        return prices if prices else None

    except Exception as e:
        logger.warning(f"Failed to fetch prices for {coingecko_id}: {e}")
        return None


def compute_revenue_score(revenue_24h: Optional[float], tvl: Optional[float]) -> Optional[int]:
    """
    Compute revenue score (0-100) based on revenue metrics.

    Scoring heuristic:
    - Revenue-to-TVL ratio is a key efficiency metric
    - Higher daily revenue relative to TVL = better
    - Absolute revenue matters for sustainability

    Returns None if data is unavailable (excluded from composite).
    """
    if revenue_24h is None or tvl is None or tvl == 0:
        return None  # Missing data - exclude from composite

    # Annualized revenue / TVL ratio
    annual_revenue = revenue_24h * 365
    ratio = annual_revenue / tvl

    # Score based on ratio (typical range 0-20%)
    # >10% ratio = excellent (90+)
    # 5-10% = good (70-90)
    # 2-5% = moderate (50-70)
    # <2% = low (30-50)
    if ratio >= 0.10:
        return min(95, 90 + int((ratio - 0.10) * 100))
    elif ratio >= 0.05:
        return 70 + int((ratio - 0.05) / 0.05 * 20)
    elif ratio >= 0.02:
        return 50 + int((ratio - 0.02) / 0.03 * 20)
    else:
        return max(30, 30 + int(ratio / 0.02 * 20))
