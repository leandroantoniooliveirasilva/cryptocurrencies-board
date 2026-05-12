"""Qualitative scoring via an LLM agent CLI (``claude --print`` by default,
``cursor-agent --print`` when ``LLM_AGENT_CLI=cursor``)."""

import json
import logging
import os
import subprocess
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


REGULATORY_PROMPT = """Score the regulatory trajectory for {symbol} ({name}) on a 0-100 scale.

Consider:
- Jurisdictional clarity (is the asset's legal status settled in major markets like US, EU, UK?)
- Recent enforcement actions or favorable rulings
- Protocol-level compliance features
- Institutional adoption as a regulatory signal
- ETF approvals or applications

Return ONLY a JSON object: {{"score": <int 0-100>, "rationale": "<1-2 sentences>"}}
No other text."""

INSTITUTIONAL_PROMPT = """Score the institutional adoption for {symbol} ({name}) on a 0-100 scale.

Consider:
- Major fund/company holdings or investments
- ETF products available
- Custody solutions from major providers
- Integration with traditional finance infrastructure
- Corporate treasury adoption
- Presence on institutional trading platforms

Return ONLY a JSON object: {{"score": <int 0-100>, "rationale": "<1-2 sentences>"}}
No other text."""

VALUE_CAPTURE_PROMPT = """Score value capture for {symbol} ({name}) on a 0-100 scale.

Focus on fees and economics that accrue to token holders (burns, staking yield net of inflation, treasury take rate, buybacks)—not supply-side fees that only go to miners/LPs with zero holder accrual.

Research and consider:
- Holder-accruing protocol revenue, burns, and real yield vs issuance
- For oracles: fee streams to the protocol/token, staking, reserves
- For L1/L2: base-fee burn, tips to stakers, net issuance after burn
- For DeFi: trading fees to treasury, Rev/TVL, earnings after incentives
- Recent trends vs peers in the same category

Use your knowledge of recent reports and public data. If exact figures aren't available, estimate from documented activity.

Return ONLY a JSON object: {{"score": <int 0-100>, "rationale": "<1-2 sentences>"}}
No other text."""

ADOPTION_ACTIVITY_PROMPT = """Score network adoption and usage for {symbol} ({name}) on a 0-100 scale.

Context: {hint}

Consider the metrics that matter for this asset class (e.g. TVL, active users, TPS, TVS for oracles, validators, ODL volume, AVS count, rollups on DA, subnet activity).

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
    full_prompt = f'{SCORING_SYSTEM_PREFIX}{prompt}'
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
