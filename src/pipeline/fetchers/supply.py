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
import threading
from datetime import datetime, timezone
from typing import Optional

import requests

from pipeline.repo_paths import repo_root

from ._agent_cli import agent_install_hint, agent_label, build_agent_command

logger = logging.getLogger(__name__)

# CoinGecko provides some supply metrics for free
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
COINGECKO_PRO_BASE = "https://pro-api.coingecko.com/api/v3"
TIMEOUT = 30

# Rate limiting for CoinGecko API (free tier = 10-30 calls/min)
RATE_LIMIT_DELAY = 3.0  # seconds between requests
MAX_RETRIES = 3
_last_request_time = 0.0
_rate_limit_lock = threading.Lock()

# Per-invocation timeout for supply scoring. ``LLM_AGENT_SUPPLY_TIMEOUT`` is the
# generic name; ``CURSOR_AGENT_SUPPLY_TIMEOUT`` kept for backwards compat.
LLM_AGENT_SUPPLY_TIMEOUT = int(
    os.environ.get('LLM_AGENT_SUPPLY_TIMEOUT',
                   os.environ.get('CURSOR_AGENT_SUPPLY_TIMEOUT', '60'))
)

REPO_ROOT = repo_root()
SCORING_SKILL_FILE = REPO_ROOT / '.agents' / 'skills' / 'crypto-scoring' / 'instructions.md'


def _load_scoring_skill_excerpt(max_chars: int = 2400) -> str:
    try:
        text = SCORING_SKILL_FILE.read_text(encoding='utf-8').strip()
    except OSError:
        return ''
    if not text:
        return ''
    return text[:max_chars]


SCORING_SKILL_EXCERPT = _load_scoring_skill_excerpt()
SCORING_SYSTEM_PREFIX = (
    'Apply this scoring skill guidance for this single-asset evaluation.\n'
    'Use concrete evidence for tokenomics and avoid placeholder rationales.\n\n'
    f'{SCORING_SKILL_EXCERPT}\n\n'
) if SCORING_SKILL_EXCERPT else ''


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


DATA_FRESHNESS_PRINCIPLES = """Treat this as a real-time supply analysis. Today is {today} (UTC).

Time-sensitive supply metrics — verify against live external sources covering the LAST ~30–60 DAYS before quoting any figure:
- Exchange reserves (BTC/ETH/etc on CEX, net flow direction)
- Staked / locked supply % and recent change
- Long-term holder share, whale concentration, top-N wallet share
- Active circulating supply vs dormant supply
- Recent unlocks, emissions, or burns

Durable tokenomics facts — use as context without re-verifying:
- Max / fixed supply cap and emission curve design
- Hard-coded burn or fee-sink mechanisms
- Vesting schedule structure for team / VC / foundation
- Mainnet launch and genesis distribution

Rules:
- Use any external research tools available (web search / fetch) to look up current values. Prefer Glassnode, CryptoQuant, Coin Metrics, DefiLlama, official validator dashboards, on-chain explorers, and project tokenomics pages.
- When citing exchange reserves, staked %, or holder concentration, append a short source tag and approximate date — e.g. "(CryptoQuant, May 2026)", "(beaconcha.in, last 30d)".
- If on-chain metrics for this asset cannot be verified within the last ~60 days, fall back to durable tokenomics (cap, emissions, burn) and score conservatively. State the data gap explicitly in the rationale rather than inventing specifics.
- Do not anchor on figures from earlier scoring runs."""


def _freshness_block() -> str:
    return DATA_FRESHNESS_PRINCIPLES.format(today=_today_utc())


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

SUPPLY_PROMPT = """Analyze the supply dynamics and on-chain metrics for {symbol} ({name}).

Score SUPPLY on a 0-100 scale (higher = more bullish tokenomics). Mix durable token-design facts with LIVE on-chain readings from the last ~30 days.

1. **Tokenomics** (weight: 30%) — DURABLE, cite from documentation
   - Max/fixed supply cap (bullish if present)
   - Emission/inflation schedule (low/declining = bullish)
   - Circulating vs total supply ratio (high = bullish, tokens already distributed)

2. **Exchange Reserves** (weight: 30%) — TIME-SENSITIVE, verify externally
   - Are exchange reserves declining over the last 30 days? (bullish — accumulation)
   - Net direction of CEX flows (inflow vs outflow)
   - Coins moving to cold storage / self-custody

3. **Holder Distribution** (weight: 25%) — TIME-SENSITIVE, verify externally
   - Current long-term holder share and recent change
   - Top-N wallet concentration and whale net position change
   - Recent accumulation vs distribution by cohort

4. **Staking / Lock-ups** (weight: 15%) — TIME-SENSITIVE for the live %, durable for design
   - Current % of TOTAL supply staked or locked (verify recent value)
   - 30-day trend of staking % — RISING = more supply removed from float (scarcity) AND a confidence signal that holders are committing to the project's future; FALLING during price strength often precedes distribution
   - Upcoming unlocks / cliffs in the next 30–90 days (verify against a vesting tracker)
   - Team/VC vesting design (durable)
   - Skip the live % factor if the asset has no native staking mechanism; lean on lock-up / vesting structure instead

Consensus-conditional factors — fold into the relevant pillar above:

A. **Proof-of-Work assets only** (e.g. BTC, KAS) — current network hash rate AND its 30-day trend. Hash rate is the supply-side security budget signal: rising hash rate = miner conviction and a healthier security budget; sustained drop = miner capitulation, weaker security, potential distribution as miners sell to cover costs. Verify via blockchain.com, mempool.space, hashrateindex, KasFYI, or chain-specific dashboards. Treat this as an additional input to Holder Distribution / Exchange Reserves reasoning (miners are a structural seller cohort).

B. **Proof-of-Stake / native-staking assets** — emphasise the live staking-% trend in pillar 4. Note specifically whether the staked supply is growing faster, in line with, or slower than circulating supply growth (issuance-adjusted), since net-new locks are what actually tighten float.

Current supply data from CoinGecko (verify it is still current; CoinGecko may lag):
{supply_data}

For each driver, prefer recent on-chain figures and cite a short source tag with approximate date when the figure materially moves the score. If on-chain data for this asset is unavailable in the last ~60 days, lean on durable tokenomics, score conservatively, and state the gap explicitly.

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


def score_supply(symbol: str, name: str, coingecko_id: str = None, use_cache: bool = True) -> Optional[dict]:
    """
    Score supply dynamics using data + LLM analysis.

    Returns ``None`` when the LLM call fails. The orchestrator handles retries
    and prior-score fallback — no hardcoded or data-only fallback is applied
    here so that composites do not drift between strong and neutral defaults.
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

    result = _invoke_agent_supply(
        SUPPLY_PROMPT.format(symbol=symbol, name=name, supply_data=supply_str),
        cache_key
    )

    if result and _is_valid_supply_result(result):
        _supply_cache[cache_key] = result
        return result

    return None


def _is_valid_supply_result(result: dict) -> bool:
    """A scoring result is valid if it has a 0-100 score and non-empty rationale."""
    score = result.get('score')
    if not isinstance(score, (int, float)):
        return False
    if score < 0 or score > 100:
        return False
    rationale = (result.get('rationale') or '').strip()
    return bool(rationale)


def _invoke_agent_supply(prompt: str, cache_key: str) -> Optional[dict]:
    """Run the selected agent CLI for supply scoring (non-interactive)."""
    label = agent_label()
    try:
        full_prompt = f'{SCORING_SYSTEM_PREFIX}{_freshness_block()}\n\n{prompt}'
        result = subprocess.run(
            build_agent_command(full_prompt),
            capture_output=True,
            text=True,
            timeout=LLM_AGENT_SUPPLY_TIMEOUT,
        )

        if result.returncode != 0:
            logger.warning(f'{label} CLI failed for {cache_key}: {result.stderr}')
            return None

        return _parse_json_response(result.stdout, cache_key)

    except subprocess.TimeoutExpired:
        logger.warning(f'{label} CLI timeout for {cache_key}')
        return None
    except FileNotFoundError:
        logger.warning(f'{label} CLI not found. {agent_install_hint()}')
        return None
    except Exception as e:
        logger.warning(f'{label} CLI error for {cache_key}: {e}')
        return None


def _parse_json_response(text: str, cache_key: str) -> Optional[dict]:
    """Parse JSON from model response."""
    try:
        text = text.strip()

        # Find JSON object
        start = text.find("{")
        end = text.rfind("}") + 1

        if start >= 0 and end > start:
            text = text[start:end]

        return json.loads(text)

    except json.JSONDecodeError as e:
        logger.warning(f'Failed to parse model response for {cache_key}: {e}')
        return None


def compute_supply_score(
    symbol: str,
    name: str = None,
    coingecko_id: str = None,
    conn = None,
    cache_writes: Optional[list[tuple[str, str, int, str]]] = None,
    use_in_memory_cache: bool = True,
) -> Optional[dict]:
    """
    Compute supply/on-chain score (0-100) with rationale.

    Returns ``None`` when the LLM call fails. The orchestrator handles retries
    and prior-score fallback.
    """
    name = name or symbol
    result = score_supply(symbol, name, coingecko_id, use_cache=use_in_memory_cache)
    if not result:
        return None

    if conn and cache_writes is not None:
        cache_writes.append((symbol, 'supply', result['score'], result['rationale']))
    elif conn:
        from pipeline.storage import migrations
        migrations.save_qualitative_score(
            conn, symbol, 'supply', result['score'], result['rationale']
        )

    return {"score": result["score"], "rationale": result["rationale"]}


def clear_cache():
    """Clear the in-memory score cache."""
    global _supply_cache
    _supply_cache = {}
