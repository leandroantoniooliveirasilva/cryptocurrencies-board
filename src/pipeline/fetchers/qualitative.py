"""Qualitative scoring via an LLM agent CLI (``claude --print`` by default,
``cursor-agent --print`` when ``LLM_AGENT_CLI=cursor``)."""

import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from typing import Optional

from pipeline.repo_paths import repo_root

from ._agent_cli import agent_install_hint, agent_label, build_agent_command

logger = logging.getLogger(__name__)

# Cache for qualitative scores (refresh weekly)
_score_cache: dict = {}

# Per-invocation timeouts (seconds). ``LLM_AGENT_*`` are the new generic names;
# ``CURSOR_AGENT_*`` are honored for backwards compatibility.
LLM_AGENT_RUN_TIMEOUT = int(
    os.environ.get('LLM_AGENT_RUN_TIMEOUT',
                   os.environ.get('CURSOR_AGENT_RUN_TIMEOUT', '300'))
)
LLM_AGENT_ADOPTION_TIMEOUT = int(
    os.environ.get('LLM_AGENT_ADOPTION_TIMEOUT',
                   os.environ.get('CURSOR_AGENT_ADOPTION_TIMEOUT', '300'))
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
    'Use concrete evidence, avoid placeholders, and return strict JSON only.\n\n'
    f'{SCORING_SKILL_EXCERPT}\n\n'
) if SCORING_SKILL_EXCERPT else ''


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


DATA_FRESHNESS_PRINCIPLES = """Treat this as a real-time analysis. Today is {today} (UTC).

Time-sensitive metrics — verify against live external sources covering the LAST ~30–60 DAYS before quoting any figure. Memorised values from earlier in the year are routinely wrong by 20%+ and must not be relied on. Examples of metrics that decay quickly:
- ETF AUM, cumulative/recent net flows, share counts
- Corporate / fund / sovereign holdings (e.g. treasury BTC or ETH balances, 13F positions)
- TVL, protocol revenue, fee burns, validator/staking yields, MEV
- Exchange reserves, staked supply %, active addresses, TPS, oracle TVS, ODL volume, AVS counts, rollups on a DA layer
- Enforcement actions, rulings, or filings issued in the last ~60 days

Durable historical facts — use as context without re-verifying:
- Landmark regulatory events (e.g. spot ETF approvals, joint SEC/CFTC commodity guidance, MiCA enactment, court rulings)
- Long-standing partnerships, custody integrations, listed ETF products and tickers
- Token-level design (supply cap, fee model, burn mechanism, mainnet launch date)
- Major historical milestones (halvings, Merge, hardforks, major outages)

Rules:
- Use any external research tools available to you (web search / fetch) to look up the current value of a metric before citing it. Do not rely on training-data memory — those numbers age fast.
- Prefer authoritative, frequently-updated sources: SoSoValue / Farside Investors (ETF flows & AUM), issuer disclosures and 13F filings (corporate holdings), DefiLlama (TVL, revenue, fees), Glassnode / CryptoQuant (on-chain & exchange reserves), CoinGecko / CoinMarketCap (market cap, dominance, supply), official protocol dashboards, SEC EDGAR / CFTC press releases.
- When a quantitative figure materially drives the score, append a short source tag and approximate date — e.g. "(SoSoValue, May 2026)", "(Strategy 8-K, Apr 2026)", "(DefiLlama, last 30d)". Figures older than ~60 days that are not durable historical facts must be flagged as stale or omitted.
- If a metric cannot be verified within the last ~60 days, score conservatively and say so explicitly in the rationale instead of inventing a number.
- Do not anchor on figures from earlier scoring runs; treat each pass as a fresh look at current reality."""


def _freshness_block() -> str:
    return DATA_FRESHNESS_PRINCIPLES.format(today=_today_utc())


REGULATORY_PROMPT = """Score the regulatory trajectory for {symbol} ({name}) on a 0-100 scale.

Weight the score toward developments in the LAST 60 DAYS (recent enforcement actions, rulings, filings, ETF approvals or denials, new guidance), while still anchoring on durable framework events (e.g. landmark commodity classifications, MiCA, court rulings) as baseline context.

Consider:
- Jurisdictional clarity in major markets (US, EU, UK, key APAC venues) — has anything moved recently?
- Enforcement actions or favorable rulings issued recently
- Protocol-level compliance features and how they map to current rules
- ETF approvals, denials, or filings — distinguish active products from speculative filings
- Institutional adoption as a regulatory signal

Cite the recent event(s) that move the score with a short source tag and approximate date.

Return ONLY a JSON object: {{"score": <int 0-100>, "rationale": "<1-2 sentences>"}}
No other text."""

INSTITUTIONAL_PROMPT = """Score the institutional adoption for {symbol} ({name}) on a 0-100 scale.

This dimension is dominated by figures that change weekly. Before scoring, verify the current state of:
- Spot/staking ETF AUM and recent net flows (last 30 days and cumulative since launch)
- Corporate, sovereign, and fund holdings (latest disclosed balances — NOT figures from earlier in the year)
- Custody integrations and prime broker support
- Presence on regulated institutional venues and structured-product wrappers

Also consider durable institutional baselines (e.g. existence of approved ETF products, long-running custody integrations, listings on regulated exchanges) but do not let them dominate over recent flow direction.

Cite the recent figures that drive the score with a short source tag and approximate date.

Return ONLY a JSON object: {{"score": <int 0-100>, "rationale": "<1-2 sentences>"}}
No other text."""

VALUE_CAPTURE_PROMPT = """Score value capture for {symbol} ({name}) on a 0-100 scale.

Focus on fees and economics that accrue to token holders (burns, staking yield net of inflation, treasury take rate, buybacks) — not supply-side fees that only go to miners/LPs with zero holder accrual.

Use LIVE protocol data (DefiLlama, official dashboards, on-chain analytics) for the last 30 days where possible — annualised run-rates should come from recent activity, not stale year-old figures. Token-design facts (fee model, burn mechanism, emissions schedule) are durable and can be cited from documentation.

Research and consider:
- Holder-accruing protocol revenue, burns, and real yield vs issuance (recent run-rate)
- For oracles: fee streams to the protocol/token, staking, reserves (recent payouts/revenue)
- For L1/L2: base-fee burn, tips to stakers, net issuance after burn (recent epochs)
- For DeFi: trading fees to treasury, Rev/TVL, earnings after incentives (recent month)
- Recent trends vs peers in the same category

When citing revenue, fees, or TVL, append a short source tag and approximate date. If exact figures cannot be verified in the last ~60 days, estimate conservatively from documented mechanism and say so — do not invent specifics.

Return ONLY a JSON object: {{"score": <int 0-100>, "rationale": "<1-2 sentences>"}}
No other text."""

ADOPTION_ACTIVITY_PROMPT = """Score network adoption and usage for {symbol} ({name}) on a 0-100 scale.

Category context: {hint}

Always-on factors (apply to every asset — verify against LIVE sources for the last 30 days):

1. **Global trading volume** — recent 24h, 7d, and 30d global spot volume across exchanges, plus direction of travel. Rising volume = growing buyer interest; sustained collapse in volume = waning attention. Verify via CoinGecko, CoinMarketCap, or major exchange aggregators.

2. **Category-specific usage** — the metrics that matter for this asset class (TVL, active users, TPS, TVS for oracles, validators, ODL volume, AVS count, rollups on DA, subnet activity, DePIN footprint, etc.). Verify via DefiLlama, l2beat, official explorers, or protocol dashboards rather than training memory.

Conditional factors (apply only when the asset's consensus / token mechanics make them relevant):

3. **Proof-of-Work assets only** (e.g. BTC, KAS, and other PoW chains) — current network hash rate AND its 30-day trend. Rising hash rate = miners committing capital = adoption signal; falling hash rate = miner capitulation or migration. Verify via blockchain.com, mempool.space, hashrateindex, KasFYI, or chain-specific dashboards.

4. **Proof-of-Stake / assets with native staking** — current % of TOTAL supply that is staked or locked AND its 30-day trend. Rising staking % = holder confidence + reduced sell pressure; falling staking % during a price uptrend often precedes distribution. Verify via stakingrewards.com, beaconcha.in, official protocol staking dashboards, or chain explorers. Skip this factor if the asset has no meaningful native staking mechanism (e.g. pure governance tokens with no lock-up).

Scoring guidance:
- Weight the score on recent direction and level across the applicable factors above.
- Anchor durability claims (mainnet launch, long-running integrations, ecosystem footprint) on stable facts — these are context, not score drivers.
- When you cite a level or growth figure (volume, hash rate, staking %, TVL), append a short source tag and approximate date — e.g. "(CoinGecko, May 2026)", "(hashrateindex, last 30d)", "(stakingrewards.com, 2026-05)".
- If a factor cannot be verified within the last ~60 days, score it conservatively and say so explicitly rather than invent a number.

Return ONLY a JSON object: {{"score": <int 0-100>, "rationale": "<1-2 sentences>"}}
No other text."""


def score_regulatory(symbol: str, name: str, use_cache: bool = True) -> Optional[dict]:
    """
    Score regulatory trajectory via the LLM agent.

    Returns ``None`` when the LLM call fails. The orchestrator handles
    retries and prior-score fallback — no hardcoded fallback is applied here.
    """
    cache_key = f"regulatory_{symbol}"

    if use_cache and cache_key in _score_cache:
        return _score_cache[cache_key]

    result = _query_scoring_llm(
        REGULATORY_PROMPT.format(symbol=symbol, name=name), cache_key
    )

    if result and _is_valid_score(result):
        _score_cache[cache_key] = result
        return result

    return None


def score_institutional(symbol: str, name: str, use_cache: bool = True) -> Optional[dict]:
    """
    Score institutional adoption via the LLM agent.

    Returns ``None`` when the LLM call fails. The orchestrator handles
    retries and prior-score fallback — no hardcoded fallback is applied here.
    """
    cache_key = f"institutional_{symbol}"

    if use_cache and cache_key in _score_cache:
        return _score_cache[cache_key]

    result = _query_scoring_llm(
        INSTITUTIONAL_PROMPT.format(symbol=symbol, name=name), cache_key
    )

    if result and _is_valid_score(result):
        _score_cache[cache_key] = result
        return result

    return None


def _is_valid_score(result: dict) -> bool:
    """A scoring result is valid if it has a numeric 0-100 score and non-empty rationale."""
    score = result.get('score')
    if not isinstance(score, (int, float)):
        return False
    if score < 0 or score > 100:
        return False
    rationale = (result.get('rationale') or '').strip()
    return bool(rationale)


def _query_scoring_llm(
    prompt: str,
    cache_key: str,
    cli_timeout: Optional[int] = None,
) -> Optional[dict]:
    """Run prompt through the selected agent CLI and parse JSON response."""
    full_prompt = f'{SCORING_SYSTEM_PREFIX}{_freshness_block()}\n\n{prompt}'
    return _invoke_agent_run(full_prompt, cache_key, timeout_sec=cli_timeout)


def _invoke_agent_run(
    prompt: str,
    cache_key: str,
    timeout_sec: Optional[int] = None,
) -> Optional[dict]:
    """Run the selected agent CLI in non-interactive mode."""
    limit = timeout_sec if timeout_sec is not None else LLM_AGENT_RUN_TIMEOUT
    label = agent_label()
    try:
        result = subprocess.run(
            build_agent_command(prompt),
            capture_output=True,
            text=True,
            timeout=limit,
        )

        if result.returncode != 0:
            logger.warning(f'{label} CLI error for {cache_key}: {result.stderr}')
            return None

        text = result.stdout.strip()
        return _parse_json_response(text, cache_key)

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
        # Handle potential markdown code blocks
        if "```" in text:
            # Extract content between code blocks
            parts = text.split("```")
            for part in parts[1:]:
                # Check for a language marker like ```json / ```JSON / ```Json
                if part[:4].lower() == "json":
                    text = part[4:].strip()
                    break
                elif part.strip().startswith("{"):
                    text = part.strip()
                    break

        # Find JSON object in text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            text = text[start:end]

        return json.loads(text)

    except json.JSONDecodeError as e:
        logger.warning(f'Failed to parse model response for {cache_key}: {e}')
        logger.debug(f"Response was: {text[:500]}")
        return None


def score_value_capture(symbol: str, name: str, use_cache: bool = True) -> Optional[dict]:
    """
    Score value capture via the LLM agent.

    Returns ``None`` when the LLM call fails. On success the result includes
    ``estimated=True`` to mark it as model-derived rather than API-derived.
    """
    cache_key = f"value_capture_{symbol}"

    if use_cache and cache_key in _score_cache:
        return _score_cache[cache_key]

    result = _query_scoring_llm(
        VALUE_CAPTURE_PROMPT.format(symbol=symbol, name=name), cache_key
    )

    if result and _is_valid_score(result):
        result['estimated'] = True
        _score_cache[cache_key] = result
        return result

    return None


def score_revenue(symbol: str, name: str, use_cache: bool = True) -> Optional[dict]:
    """Backward-compatible alias for score_value_capture."""
    return score_value_capture(symbol, name, use_cache)


def score_adoption_activity(
    symbol: str,
    name: str,
    hint: str,
    use_cache: bool = True,
) -> Optional[dict]:
    """
    Score adoption / network activity via the LLM agent.

    Returns ``None`` when the LLM call fails.
    """
    cache_key = f"adoption_activity_{symbol}"

    if use_cache and cache_key in _score_cache:
        return _score_cache[cache_key]

    result = _query_scoring_llm(
        ADOPTION_ACTIVITY_PROMPT.format(symbol=symbol, name=name, hint=hint),
        cache_key,
        cli_timeout=LLM_AGENT_ADOPTION_TIMEOUT,
    )

    if result and _is_valid_score(result):
        _score_cache[cache_key] = result
        return result

    return None


def clear_cache():
    """Clear the score cache (call before weekly refresh)."""
    global _score_cache
    _score_cache = {}
