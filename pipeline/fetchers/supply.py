"""Supply and on-chain metrics fetcher.

This module provides supply-side metrics that indicate accumulation/distribution:
- Exchange reserves (declining = bullish)
- Long-term holder supply percentage
- Supply concentration metrics
- Tokenomics (max supply, inflation, circulating ratio)

Combines actual supply data from CoinGecko with AI-based qualitative assessment.
"""

import json
import logging
import os
import subprocess
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# CoinGecko provides some supply metrics for free
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
COINGECKO_PRO_BASE = "https://pro-api.coingecko.com/api/v3"
TIMEOUT = 30

# Rate limiting for CoinGecko API (free tier = 10-30 calls/min)
RATE_LIMIT_DELAY = 3.0  # seconds between requests
MAX_RETRIES = 3
_last_request_time = 0.0

# Claude model for qualitative scoring (configurable via env)
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "opus")


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


def _get_headers() -> dict:
    """Get headers with API key if available."""
    api_key = os.environ.get("COINGECKO_API_KEY")
    if api_key:
        return {"x-cg-pro-api-key": api_key}
    return {}


def _get_base_url() -> str:
    """Get base URL based on API key availability."""
    if os.environ.get("COINGECKO_API_KEY"):
        return COINGECKO_PRO_BASE
    return COINGECKO_BASE

# In-memory cache for AI scores (persisted to DB separately)
_supply_cache: dict = {}

USE_CLI = os.environ.get("USE_CLAUDE_CLI", "true").lower() == "true"

SUPPLY_PROMPT = """Analyze the supply dynamics and on-chain metrics for {symbol} ({name}).

Consider these factors for a SUPPLY score (0-100 scale, higher = more bullish tokenomics):

1. **Tokenomics** (weight: 30%)
   - Is there a max/fixed supply cap? (bullish)
   - What's the emission/inflation schedule? (low/declining = bullish)
   - Circulating vs total supply ratio (high = bullish, tokens already distributed)

2. **Exchange Reserves** (weight: 30%)
   - Are exchange reserves declining? (bullish - accumulation)
   - Are coins moving to cold storage/self-custody? (bullish)

3. **Holder Distribution** (weight: 25%)
   - What % is held by long-term holders? (high = bullish)
   - Is there concerning concentration in few wallets?
   - Whale behavior patterns

4. **Staking/Lock-ups** (weight: 15%)
   - What % of supply is staked or locked? (high = reduced sell pressure)
   - Lock-up schedules for team/VC tokens

Current supply data from CoinGecko:
{supply_data}

Return ONLY a JSON object: {{"score": <int 0-100>, "rationale": "<2-3 sentences explaining key supply factors>"}}
No other text."""


def fetch_supply_metrics(coingecko_id: str) -> Optional[dict]:
    """
    Fetch supply metrics from CoinGecko.

    Args:
        coingecko_id: CoinGecko coin ID

    Returns:
        Dict with supply metrics or None
    """
    if not coingecko_id:
        return None

    try:
        url = f"{_get_base_url()}/coins/{coingecko_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "community_data": "false",
            "developer_data": "false",
        }

        # Rate limiting and retry logic
        for attempt in range(MAX_RETRIES):
            _rate_limit()
            resp = requests.get(url, params=params, headers=_get_headers(), timeout=TIMEOUT)

            if resp.status_code == 429:
                wait_time = 5 * (2 ** attempt)
                logger.info(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}/{MAX_RETRIES}")
                time.sleep(wait_time)
                continue

            resp.raise_for_status()
            break
        else:
            logger.warning(f"Max retries exceeded fetching supply for {coingecko_id}")
            return None

        data = resp.json()

        market_data = data.get("market_data", {})
        circulating = market_data.get("circulating_supply")
        total = market_data.get("total_supply")
        max_supply = market_data.get("max_supply")

        return {
            "circulating_supply": circulating,
            "total_supply": total,
            "max_supply": max_supply,
            "circulating_ratio": circulating / total if circulating and total and total > 0 else None,
            "inflation_ratio": (total - circulating) / circulating if circulating and total and circulating > 0 else None,
            "has_max_supply": max_supply is not None,
        }

    except Exception as e:
        logger.debug(f"Failed to fetch supply metrics for {coingecko_id}: {e}")
        return None


def score_supply(symbol: str, name: str, coingecko_id: str = None, use_cache: bool = True) -> dict:
    """
    Score supply dynamics using data + AI analysis.

    Args:
        symbol: Asset symbol (e.g., 'BTC')
        name: Asset name (e.g., 'Bitcoin')
        coingecko_id: CoinGecko ID for fetching supply data
        use_cache: Whether to use cached scores

    Returns:
        Dict with 'score' (int) and 'rationale' (str)
    """
    cache_key = f"supply_{symbol}"

    if use_cache and cache_key in _supply_cache:
        return _supply_cache[cache_key]

    # Fetch actual supply data
    supply_data = fetch_supply_metrics(coingecko_id) if coingecko_id else None

    # Format supply data for AI prompt
    if supply_data:
        supply_str = json.dumps({
            "circulating_supply": f"{supply_data['circulating_supply']:,.0f}" if supply_data['circulating_supply'] else "Unknown",
            "total_supply": f"{supply_data['total_supply']:,.0f}" if supply_data['total_supply'] else "Unknown",
            "max_supply": f"{supply_data['max_supply']:,.0f}" if supply_data['max_supply'] else "No cap",
            "circulating_ratio": f"{supply_data['circulating_ratio']:.1%}" if supply_data['circulating_ratio'] else "Unknown",
            "has_fixed_supply": supply_data['has_max_supply'],
        }, indent=2)
    else:
        supply_str = "No supply data available - assess based on known tokenomics"

    result = _query_claude(
        SUPPLY_PROMPT.format(symbol=symbol, name=name, supply_data=supply_str),
        cache_key
    )

    if result:
        _supply_cache[cache_key] = result
        return result

    # Fallback: compute from data if AI fails
    return _compute_fallback_score(symbol, supply_data)


def _query_claude(prompt: str, cache_key: str) -> Optional[dict]:
    """Query Claude CLI for supply scoring."""
    if not USE_CLI:
        return None

    try:
        result = subprocess.run(
            ["claude", "--print", "--model", CLAUDE_MODEL, prompt],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            logger.warning(f"Claude CLI failed for {cache_key}: {result.stderr}")
            return None

        return _parse_json_response(result.stdout, cache_key)

    except subprocess.TimeoutExpired:
        logger.warning(f"Claude CLI timeout for {cache_key}")
        return None
    except FileNotFoundError:
        logger.warning("Claude CLI not found")
        return None
    except Exception as e:
        logger.warning(f"Claude CLI error for {cache_key}: {e}")
        return None


def _parse_json_response(text: str, cache_key: str) -> Optional[dict]:
    """Parse JSON from Claude response."""
    try:
        text = text.strip()

        # Find JSON object
        start = text.find("{")
        end = text.rfind("}") + 1

        if start >= 0 and end > start:
            text = text[start:end]

        return json.loads(text)

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse Claude response for {cache_key}: {e}")
        return None


def _compute_fallback_score(symbol: str, supply_data: Optional[dict]) -> dict:
    """
    Compute supply score from data when AI is unavailable.

    Starts at 50 (neutral) and adjusts based on available metrics.
    """
    score = 50
    factors = []

    if supply_data:
        # Max supply cap is bullish (+10)
        if supply_data.get("has_max_supply"):
            score += 10
            factors.append("fixed supply cap")

        # High circulating ratio is bullish (tokens already distributed)
        circ_ratio = supply_data.get("circulating_ratio")
        if circ_ratio is not None:
            if circ_ratio >= 0.9:
                score += 15
                factors.append("90%+ circulating")
            elif circ_ratio >= 0.7:
                score += 8
                factors.append("70%+ circulating")
            elif circ_ratio < 0.5:
                score -= 10
                factors.append("low circulating ratio")

        # Low inflation is bullish
        inflation = supply_data.get("inflation_ratio")
        if inflation is not None:
            if inflation < 0.02:
                score += 10
                factors.append("minimal inflation")
            elif inflation < 0.05:
                score += 5
                factors.append("low inflation")
            elif inflation > 0.15:
                score -= 10
                factors.append("high inflation")

    # Clamp score
    score = max(0, min(100, score))

    rationale = f"Data-driven score. {', '.join(factors).capitalize()}." if factors else "Limited supply data available."

    return {"score": score, "rationale": rationale}


def compute_supply_score(
    symbol: str,
    name: str = None,
    coingecko_id: str = None,
    conn = None,
) -> dict:
    """
    Compute supply/on-chain score (0-100) with rationale.

    This is the main entry point - uses cached DB scores or computes fresh.

    Args:
        symbol: Asset symbol
        name: Asset name (for AI prompt)
        coingecko_id: CoinGecko ID for supply data
        conn: Database connection for caching

    Returns:
        Dict with 'score' (int 0-100) and 'rationale' (str)
    """
    # Try to get cached score from database
    if conn:
        from pipeline.storage import migrations
        cached = migrations.get_cached_qualitative_score(conn, symbol, "supply")
        if cached:
            return {"score": cached["score"], "rationale": cached["rationale"]}

    # Compute fresh score
    name = name or symbol
    result = score_supply(symbol, name, coingecko_id)

    # Handle case where result is None (shouldn't happen but defensive)
    if not result:
        logger.warning(f"Failed to compute supply score for {symbol}, using fallback")
        result = _compute_fallback_score(symbol, None)

    # Cache to database
    if conn:
        from pipeline.storage import migrations
        migrations.save_qualitative_score(
            conn, symbol, "supply",
            result["score"], result["rationale"]
        )

    return {"score": result["score"], "rationale": result["rationale"]}


def clear_cache():
    """Clear the in-memory score cache."""
    global _supply_cache
    _supply_cache = {}
