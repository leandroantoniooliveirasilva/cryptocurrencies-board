"""CoinGecko API fetcher for OHLC and price data."""

import logging
import os
import time
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


def _rate_limit():
    """Enforce rate limiting between requests."""
    global _last_request_time
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

    Args:
        ohlc_data: List of [timestamp, open, high, low, close]

    Returns:
        List of closing prices (oldest to newest)
    """
    if not ohlc_data:
        return []

    # CoinGecko returns 4-hour candles for 30d, daily for 90d+
    # Extract close prices (index 4)
    closes = [candle[4] for candle in ohlc_data if len(candle) >= 5]
    return closes


def extract_weekly_closes(ohlc_data: list[list]) -> list[float]:
    """
    Extract weekly closing prices from daily OHLC data.

    Args:
        ohlc_data: List of [timestamp, open, high, low, close]

    Returns:
        List of weekly closing prices (oldest to newest)
    """
    if not ohlc_data:
        return []

    # Sample every 7th candle (approximately weekly)
    # For more accuracy, would need to aggregate by actual week
    closes = [candle[4] for candle in ohlc_data if len(candle) >= 5]

    # Return every 7th value (or last 4 weeks worth)
    weekly = closes[::7] if len(closes) >= 7 else closes
    return weekly[-4:] if len(weekly) > 4 else weekly
