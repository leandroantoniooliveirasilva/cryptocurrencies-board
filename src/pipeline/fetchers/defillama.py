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

# Process-level cache for /v2/chains (large payload, refreshed per run).
_chains_cache: Optional[list[dict]] = None


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
        # Fetch TVL from the protocol endpoint first.
        tvl_data = _fetch_tvl(slug)
        tvl_value = tvl_data.get("tvl") if tvl_data else None

        # Fallback for L1 chains (e.g. solana, sui, avalanche): DefiLlama's
        # /protocol/{slug} for these points to a "Canonical Bridge" entry with
        # no meaningful TVL. Chain-level TVL lives under /v2/chains instead.
        if tvl_value is None or tvl_value == 0:
            chain_tvl = _fetch_chain_tvl(slug)
            if chain_tvl is not None:
                tvl_value = chain_tvl

        # Fetch fees and revenue. DefiLlama's /summary/fees/{slug} returns:
        # - total24h: total fees paid by users
        # - With dataType=dailyRevenue: protocol revenue (for protocols, often
        #   a portion of fees; for chains, typically burned tokens)
        #
        # For L1 chains (category="Chain"), the relevant metric is total fees,
        # not "protocol revenue" which may just be burned tokens. For protocols,
        # we use the dailyRevenue endpoint which captures their actual revenue.
        fees_data = _fetch_fees(slug)
        fees_24h = fees_data.get("total24h") if fees_data else None
        category = fees_data.get("category") if fees_data else None

        # For L1 chains, use total fees as revenue (chains earn from tx fees)
        # For protocols, fetch explicit dailyRevenue (their cut of fees)
        if category == "Chain":
            revenue_24h = fees_24h
        else:
            revenue_data = _fetch_fees(slug, data_type="dailyRevenue")
            revenue_24h = revenue_data.get("total24h") if revenue_data else None

        # Fallback: if dailyRevenue is 0 but fees exist, use fees as revenue proxy
        # This handles protocols like oracles where "fees" are the revenue model
        # but DefiLlama doesn't separate them into "protocol revenue"
        if (revenue_24h is None or revenue_24h == 0) and fees_24h and fees_24h > 0:
            revenue_24h = fees_24h
            logger.debug(f"Using fees as revenue proxy for {slug}: ${fees_24h:.0f}")

        return {
            "tvl": tvl_value,
            "fees_24h": fees_24h,
            "revenue_24h": revenue_24h,
        }

    except Exception as e:
        logger.warning(f"Failed to fetch DefiLlama data for {slug}: {e}")
        return None


def _fetch_chain_tvl(slug: str) -> Optional[float]:
    """Return the current chain TVL for `slug` if it matches a DefiLlama chain.

    Matches the DefiLlama slug against each chain's `name` or `gecko_id`
    (case-insensitive). Returns None if no match or on API failure.
    """
    global _chains_cache
    if _chains_cache is None:
        time.sleep(REQUEST_DELAY)
        try:
            resp = requests.get(f"{BASE_URL}/v2/chains", timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            _chains_cache = data if isinstance(data, list) else []
        except Exception as e:
            logger.debug(f"Chain list fetch failed: {e}")
            _chains_cache = []

    needle = slug.lower()
    for chain in _chains_cache:
        name = (chain.get("name") or "").lower()
        gecko = (chain.get("gecko_id") or "").lower()
        if needle in (name, gecko):
            tvl = chain.get("tvl")
            if isinstance(tvl, (int, float)):
                return float(tvl)
            return None
    return None


def _fetch_tvl(slug: str) -> Optional[dict]:
    """Fetch TVL data for a protocol.

    The DefiLlama /protocol/{slug} response exposes `tvl` as a time series
    (list of {date, totalLiquidityUSD}) and `currentChainTvls` as a per-chain
    map (no aggregate "total" key). We extract the most recent total from the
    time series, falling back to summing current chain TVLs while skipping
    synthetic entries (borrowed, staking, pool2, and chain-scoped variants).
    """
    time.sleep(REQUEST_DELAY)
    try:
        resp = requests.get(f"{BASE_URL}/protocol/{slug}", timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        # Preferred: last point of the aggregate TVL time series.
        series = data.get("tvl")
        if isinstance(series, list) and series:
            last = series[-1]
            if isinstance(last, dict):
                tvl_value = last.get("totalLiquidityUSD")
                if isinstance(tvl_value, (int, float)):
                    return {"tvl": tvl_value}

        # Fallback: sum currentChainTvls across real chains only.
        chain_tvls = data.get("currentChainTvls") or {}
        skip_suffixes = ("-borrowed", "-staking", "-pool2", "-treasury", "-vesting")
        skip_exact = {"borrowed", "staking", "pool2", "treasury", "vesting"}
        total = 0.0
        found = False
        for key, value in chain_tvls.items():
            if not isinstance(value, (int, float)):
                continue
            if key in skip_exact or key.endswith(skip_suffixes):
                continue
            total += value
            found = True
        if found:
            return {"tvl": total}

        return {"tvl": None}
    except Exception as e:
        logger.debug(f"TVL fetch failed for {slug}: {e}")
        return None


def _fetch_fees(slug: str, data_type: Optional[str] = None) -> Optional[dict]:
    """
    Fetch fees or revenue data for a protocol.

    Args:
        slug: DefiLlama protocol slug.
        data_type: Optional DefiLlama dataType parameter. Pass "dailyRevenue"
            to retrieve daily revenue (returned in `total24h`). When omitted,
            the endpoint returns daily fees in `total24h`.
    """
    time.sleep(REQUEST_DELAY)
    try:
        params = {"dataType": data_type} if data_type else None
        resp = requests.get(
            f"{BASE_URL}/summary/fees/{slug}",
            params=params,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.debug(f"Fees fetch failed for {slug} (dataType={data_type}): {e}")
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
    dated = fetch_daily_prices_with_timestamps(coingecko_id, days)
    if not dated:
        return None
    return [price for _ts, price in dated]


def fetch_daily_prices_with_timestamps(
    coingecko_id: str, days: int = 120
) -> Optional[list[tuple[int, float]]]:
    """
    Fetch daily closing prices from DefiLlama, preserving timestamps.

    Args:
        coingecko_id: CoinGecko coin ID (e.g., 'bitcoin', 'solana')
        days: Number of days of history

    Returns:
        List of (unix_timestamp_seconds, price) tuples (oldest to newest) or None
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
        dated = [
            (int(p["timestamp"]), float(p["price"]))
            for p in prices_data
            if "price" in p and "timestamp" in p
        ]
        # Ensure chronological order (oldest to newest)
        dated.sort(key=lambda row: row[0])
        return dated if dated else None

    except Exception as e:
        logger.warning(f"Failed to fetch prices for {coingecko_id}: {e}")
        return None


def compute_revenue_score(revenue_24h: Optional[float], tvl: Optional[float]) -> Optional[int]:
    """
    Compute revenue score (0-100) based on revenue metrics.

    Scoring heuristics:
    1. For protocols WITH TVL: Revenue-to-TVL ratio (capital efficiency)
    2. For protocols WITHOUT TVL (oracles, infra): Absolute revenue tiers

    Returns None if no revenue data available.
    """
    if revenue_24h is None:
        return None  # No revenue data at all

    # For protocols without TVL (oracles, infrastructure), use absolute revenue tiers
    # These protocols don't have locked value but still generate fees
    if tvl is None or tvl == 0:
        annual_revenue = revenue_24h * 365
        # Absolute revenue scoring (annualized):
        # >$50M/year = excellent (85+)
        # $10-50M = strong (70-84)
        # $1-10M = moderate (50-69)
        # <$1M = limited (30-49)
        if annual_revenue >= 50_000_000:
            return min(95, 85 + int((annual_revenue - 50_000_000) / 50_000_000 * 10))
        elif annual_revenue >= 10_000_000:
            return 70 + int((annual_revenue - 10_000_000) / 40_000_000 * 14)
        elif annual_revenue >= 1_000_000:
            return 50 + int((annual_revenue - 1_000_000) / 9_000_000 * 19)
        elif annual_revenue > 0:
            return max(30, 30 + int(annual_revenue / 1_000_000 * 19))
        else:
            return 30  # Zero revenue

    # For protocols with TVL: use revenue-to-TVL ratio
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
