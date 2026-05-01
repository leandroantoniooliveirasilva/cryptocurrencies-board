"""CoinGecko API fetcher for OHLC and price data."""

import logging
import os
import time
import threading
from typing import Optional

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://api.coingecko.com/api/v3"
PRO_BASE_URL = "https://pro-api.coingecko.com/api/v3"
TIMEOUT = 30

# Rate limiting: free tier = 10-30 calls/min depending on endpoint
RATE_LIMIT_DELAY = 3.0  # seconds between requests
MAX_RETRIES = 3
_last_request_time = 0.0
_rate_limit_lock = threading.Lock()


def _rate_limit():
    """Enforce rate limiting between requests."""
    global _last_request_time
    with _rate_limit_lock:
        now = time.time()
        elapsed = now - _last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            sleep_time = RATE_LIMIT_DELAY - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
        _last_request_time = time.time()


def _request_with_retry(url: str, params: dict, headers: dict) -> Optional[requests.Response]:
    """Make request with retry on 429 errors."""
    global _last_request_time

    for attempt in range(MAX_RETRIES):
        _rate_limit()
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)

            if resp.status_code == 429:
                # Exponential backoff: 5s, 10s, 20s
                wait_time = 5 * (2 ** attempt)
                logger.info(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}/{MAX_RETRIES}")
                time.sleep(wait_time)
                _last_request_time = time.time()
                continue

            resp.raise_for_status()
            return resp

        except requests.exceptions.HTTPError as e:
            if "429" in str(e) and attempt < MAX_RETRIES - 1:
                wait_time = 5 * (2 ** attempt)
                logger.info(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}/{MAX_RETRIES}")
                time.sleep(wait_time)
                _last_request_time = time.time()
                continue
            raise

    logger.warning(f"Max retries ({MAX_RETRIES}) exceeded for {url}")
    return None


def _get_headers() -> dict:
    """Get headers with API key if available."""
    api_key = os.environ.get("COINGECKO_API_KEY")
    if api_key:
        return {"x-cg-pro-api-key": api_key}
    return {}


def _get_base_url() -> str:
    """Get base URL based on API key availability."""
    if os.environ.get("COINGECKO_API_KEY"):
        return PRO_BASE_URL
    return BASE_URL


def fetch_ohlc(
    coin_id: str, vs_currency: str = "usd", days: int = 30
) -> Optional[list[list]]:
    """
    Fetch OHLC data from CoinGecko.

    Args:
        coin_id: CoinGecko coin ID (e.g., 'bitcoin', 'solana')
        vs_currency: Quote currency (default 'usd')
        days: Number of days of data (1, 7, 14, 30, 90, 180, 365, max)

    Returns:
        List of [timestamp, open, high, low, close] or None on failure
    """
    if not coin_id:
        return None

    try:
        url = f"{_get_base_url()}/coins/{coin_id}/ohlc"
        params = {"vs_currency": vs_currency, "days": days}

        resp = _request_with_retry(url, params, _get_headers())
        if resp:
            return resp.json()
        return None

    except Exception as e:
        logger.warning(f"Failed to fetch OHLC for {coin_id}: {e}")
        return None


def fetch_price(coin_id: str, vs_currency: str = "usd") -> Optional[float]:
    """
    Fetch current price from CoinGecko.

    Args:
        coin_id: CoinGecko coin ID
        vs_currency: Quote currency

    Returns:
        Current price or None on failure
    """
    if not coin_id:
        return None

    try:
        url = f"{_get_base_url()}/simple/price"
        params = {"ids": coin_id, "vs_currencies": vs_currency}

        resp = _request_with_retry(url, params, _get_headers())
        if resp:
            data = resp.json()
            return data.get(coin_id, {}).get(vs_currency)
        return None

    except Exception as e:
        logger.warning(f"Failed to fetch price for {coin_id}: {e}")
        return None


def fetch_daily_prices(
    coin_id: str, vs_currency: str = "usd", days: int = 90
) -> Optional[list[float]]:
    """
    Fetch daily closing prices from CoinGecko market_chart endpoint.

    This endpoint returns daily data points for 90+ days, unlike OHLC
    which returns 4-day candles on free tier.

    Args:
        coin_id: CoinGecko coin ID
        vs_currency: Quote currency
        days: Number of days

    Returns:
        List of daily closing prices (oldest to newest) or None
    """
    if not coin_id:
        return None

    try:
        url = f"{_get_base_url()}/coins/{coin_id}/market_chart"
        params = {"vs_currency": vs_currency, "days": days, "interval": "daily"}

        resp = _request_with_retry(url, params, _get_headers())
        if resp:
            data = resp.json()
            prices = data.get("prices", [])
            # prices is [[timestamp, price], ...]
            return [p[1] for p in prices]
        return None

    except Exception as e:
        logger.warning(f"Failed to fetch daily prices for {coin_id}: {e}")
        return None


def fetch_market_data(coin_id: str, vs_currency: str = "usd") -> Optional[dict]:
    """
    Fetch comprehensive market data from CoinGecko.

    Args:
        coin_id: CoinGecko coin ID
        vs_currency: Quote currency

    Returns:
        Dict with market cap, volume, price change data or None on failure
    """
    if not coin_id:
        return None

    try:
        url = f"{_get_base_url()}/coins/{coin_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "community_data": "false",
            "developer_data": "false",
        }

        resp = _request_with_retry(url, params, _get_headers())
        if resp:
            data = resp.json()
            market = data.get("market_data", {})
            return {
                "price": market.get("current_price", {}).get(vs_currency),
                "market_cap": market.get("market_cap", {}).get(vs_currency),
                "total_volume": market.get("total_volume", {}).get(vs_currency),
                "price_change_24h": market.get("price_change_percentage_24h"),
                "price_change_7d": market.get("price_change_percentage_7d"),
                "price_change_30d": market.get("price_change_percentage_30d"),
            }
        return None

    except Exception as e:
        logger.warning(f"Failed to fetch market data for {coin_id}: {e}")
        return None


def extract_daily_closes(ohlc_data: list[list]) -> list[float]:
    """
    Extract daily closing prices from OHLC data.

    CoinGecko free tier returns 4-hour candles, so we aggregate to daily
    by taking the last candle of each day.

    Args:
        ohlc_data: List of [timestamp, open, high, low, close]

    Returns:
        List of daily closing prices (oldest to newest)
    """
    if not ohlc_data:
        return []

    from datetime import datetime, timezone

    # Group candles by date and take last close of each day
    daily_closes = {}
    for candle in ohlc_data:
        if len(candle) < 5:
            continue
        timestamp_ms = candle[0]
        close = candle[4]
        # Convert to date string for grouping
        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        date_key = dt.strftime("%Y-%m-%d")
        # Keep the latest candle for each day
        daily_closes[date_key] = close

    # Return closes sorted by date (oldest to newest)
    sorted_dates = sorted(daily_closes.keys())
    return [daily_closes[d] for d in sorted_dates]


def extract_weekly_closes(ohlc_data: list[list]) -> list[float]:
    """
    Extract weekly closing prices from OHLC data.

    Aggregates to weekly by taking the last candle of each ISO week.

    Args:
        ohlc_data: List of [timestamp, open, high, low, close]

    Returns:
        List of weekly closing prices (oldest to newest)
    """
    if not ohlc_data:
        return []

    from datetime import datetime, timezone

    # Group candles by ISO week and take last close of each week
    weekly_closes = {}
    for candle in ohlc_data:
        if len(candle) < 5:
            continue
        timestamp_ms = candle[0]
        close = candle[4]
        # Convert to ISO week key (year-week)
        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        year, week, _ = dt.isocalendar()
        week_key = f"{year}-W{week:02d}"
        # Keep the latest candle for each week
        weekly_closes[week_key] = close

    # Return closes sorted by week (oldest to newest)
    sorted_weeks = sorted(weekly_closes.keys())
    return [weekly_closes[w] for w in sorted_weeks]


def fetch_global_market_data() -> dict:
    """
    Fetch global market data including BTC dominance and stablecoin market cap.

    Returns:
        Dict with:
        - btc_dominance: BTC market dominance percentage
        - stablecoin_mcap: Total stablecoin market cap in USD
        - total_mcap: Total crypto market cap in USD
    """
    try:
        url = f"{_get_base_url()}/global"
        resp = _request_with_retry(url, {}, _get_headers())
        if not resp:
            logger.warning("Failed to fetch global market data")
            return {}

        data = resp.json().get("data", {})
        return {
            "btc_dominance": round(data.get("market_cap_percentage", {}).get("btc", 0), 1),
            "total_mcap": data.get("total_market_cap", {}).get("usd"),
            "stablecoin_mcap": None,  # Not directly available, need separate call
        }
    except Exception as e:
        logger.warning(f"Error fetching global data: {e}")
        return {}


def fetch_stablecoin_mcap() -> Optional[float]:
    """
    Fetch total stablecoin market cap from CoinGecko categories.

    Returns:
        Total stablecoin market cap in USD or None
    """
    try:
        url = f"{_get_base_url()}/coins/markets"
        params = {
            "vs_currency": "usd",
            "category": "stablecoins",
            "order": "market_cap_desc",
            "per_page": 20,
            "page": 1,
        }
        resp = _request_with_retry(url, params, _get_headers())
        if not resp:
            return None

        coins = resp.json()
        total = sum(c.get("market_cap", 0) or 0 for c in coins)
        return total
    except Exception as e:
        logger.warning(f"Error fetching stablecoin data: {e}")
        return None
