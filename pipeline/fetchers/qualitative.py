"""Qualitative scoring via Claude CLI for regulatory and institutional metrics."""

import json
import logging
import os
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)

# Cache for qualitative scores (refresh weekly)
_score_cache: dict = {}

# Use Claude CLI (subscription) or API
USE_CLI = os.environ.get("USE_CLAUDE_CLI", "true").lower() == "true"

# Model to use for API calls (configurable via env var)
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "opus")


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

REVENUE_PROMPT = """Score the revenue/fee generation for {symbol} ({name}) on a 0-100 scale.

Research and consider:
- Protocol fees (transaction fees, trading fees, service fees)
- Revenue model sustainability
- For oracles: data feed fees, CCIP fees, node operator payments
- For L1/L2: transaction fees, MEV revenue
- For DeFi: trading fees, interest spreads, liquidation fees
- Recent revenue trends and growth
- Revenue relative to competitors in the same category

Use your knowledge of recent reports, documentation, and public data. If exact figures aren't available, estimate based on protocol activity and adoption.

Return ONLY a JSON object: {{"score": <int 0-100>, "rationale": "<1-2 sentences explaining the revenue model and estimated strength>"}}
No other text."""


def score_regulatory(symbol: str, name: str, use_cache: bool = True) -> dict:
    """
    Score regulatory trajectory using Claude.

    Args:
        symbol: Asset symbol (e.g., 'BTC')
        name: Asset name (e.g., 'Bitcoin')
        use_cache: Whether to use cached scores

    Returns:
        Dict with 'score' (int) and 'rationale' (str)
    """
    cache_key = f"regulatory_{symbol}"

    if use_cache and cache_key in _score_cache:
        return _score_cache[cache_key]

    result = _query_claude(
        REGULATORY_PROMPT.format(symbol=symbol, name=name), cache_key
    )

    if result:
        _score_cache[cache_key] = result
        return result

    # Fallback scores based on known assets
    return _get_fallback_regulatory(symbol)


def score_institutional(symbol: str, name: str, use_cache: bool = True) -> dict:
    """
    Score institutional adoption using Claude.

    Args:
        symbol: Asset symbol (e.g., 'BTC')
        name: Asset name (e.g., 'Bitcoin')
        use_cache: Whether to use cached scores

    Returns:
        Dict with 'score' (int) and 'rationale' (str)
    """
    cache_key = f"institutional_{symbol}"

    if use_cache and cache_key in _score_cache:
        return _score_cache[cache_key]

    result = _query_claude(
        INSTITUTIONAL_PROMPT.format(symbol=symbol, name=name), cache_key
    )

    if result:
        _score_cache[cache_key] = result
        return result

    # Fallback scores based on known assets
    return _get_fallback_institutional(symbol)


def _query_claude(prompt: str, cache_key: str) -> Optional[dict]:
    """Query Claude via CLI or API and parse JSON response."""
    if USE_CLI:
        return _query_claude_cli(prompt, cache_key)
    else:
        return _query_claude_api(prompt, cache_key)


def _query_claude_cli(prompt: str, cache_key: str) -> Optional[dict]:
    """Query Claude using the CLI (subscription-based)."""
    try:
        # Use claude CLI with --print flag for non-interactive output
        result = subprocess.run(
            ["claude", "--print", "--model", CLAUDE_MODEL, prompt],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            logger.warning(f"Claude CLI error for {cache_key}: {result.stderr}")
            return None

        text = result.stdout.strip()
        return _parse_json_response(text, cache_key)

    except subprocess.TimeoutExpired:
        logger.warning(f"Claude CLI timeout for {cache_key}")
        return None
    except FileNotFoundError:
        logger.warning("Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code")
        return None
    except Exception as e:
        logger.warning(f"Claude CLI error for {cache_key}: {e}")
        return None


def _query_claude_api(prompt: str, cache_key: str) -> Optional[dict]:
    """Query Claude using the API (requires ANTHROPIC_API_KEY)."""
    try:
        import anthropic
        client = anthropic.Anthropic()

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()
        return _parse_json_response(text, cache_key)

    except ImportError:
        logger.warning("anthropic package not installed")
        return None
    except Exception as e:
        logger.warning(f"Claude API error for {cache_key}: {e}")
        return None


def _parse_json_response(text: str, cache_key: str) -> Optional[dict]:
    """Parse JSON from Claude response."""
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
        logger.warning(f"Failed to parse Claude response for {cache_key}: {e}")
        logger.debug(f"Response was: {text[:500]}")
        return None


def _get_fallback_regulatory(symbol: str) -> dict:
    """Fallback regulatory scores for known assets."""
    fallbacks = {
        "BTC": {"score": 88, "rationale": "ETF approved, commodity classification in most jurisdictions"},
        "ETH": {"score": 82, "rationale": "ETF approved, regulatory clarity improving"},
        "SOL": {"score": 78, "rationale": "Growing institutional interest, no adverse rulings"},
        "LINK": {"score": 82, "rationale": "Enterprise partnerships signal regulatory comfort"},
        "XRP": {"score": 82, "rationale": "SEC lawsuit settled favorably"},
        "AVAX": {"score": 72, "rationale": "No major regulatory issues, moderate clarity"},
        "HBAR": {"score": 78, "rationale": "Enterprise governance structure helps compliance"},
        "HYPE": {"score": 68, "rationale": "Newer protocol, regulatory status evolving"},
        "MORPHO": {"score": 70, "rationale": "DeFi lending, institutional backing signals compliance"},
        "QNT": {"score": 75, "rationale": "Enterprise-focused, regulatory engagement"},
        "XLM": {"score": 75, "rationale": "Payments focus, regulatory partnerships"},
        "KAS": {"score": 60, "rationale": "Newer PoW chain, limited regulatory clarity"},
        "AAVE": {"score": 72, "rationale": "Established DeFi, some regulatory engagement"},
        "SUI": {"score": 68, "rationale": "VC-backed L1, growing institutional presence"},
        "ONDO": {"score": 75, "rationale": "RWA focus, BlackRock partnership signals compliance"},
        "TAO": {"score": 55, "rationale": "AI-crypto, limited regulatory framework"},
        "PENDLE": {"score": 60, "rationale": "Yield trading, DeFi regulatory uncertainty"},
        "ENA": {"score": 50, "rationale": "Synthetic dollar, MiCA concerns"},
        "CANTON": {"score": 70, "rationale": "Enterprise blockchain, pre-market"},
    }
    return fallbacks.get(symbol, {"score": 65, "rationale": "Limited regulatory clarity"})


def _get_fallback_institutional(symbol: str) -> dict:
    """Fallback institutional scores for known assets."""
    fallbacks = {
        "BTC": {"score": 92, "rationale": "ETF flows, corporate treasuries, major custody support"},
        "ETH": {"score": 85, "rationale": "ETF products, DeFi infrastructure for institutions"},
        "SOL": {"score": 84, "rationale": "Growing fund holdings, major VC backing"},
        "LINK": {"score": 88, "rationale": "Enterprise integrations, oracle standard"},
        "XRP": {"score": 78, "rationale": "Banking partnerships, ETF inflows"},
        "AVAX": {"score": 72, "rationale": "RWA TVL, VanEck ETF, BlackRock fund"},
        "HBAR": {"score": 68, "rationale": "Enterprise council, limited retail-focused"},
        "HYPE": {"score": 75, "rationale": "Revenue leader, growing institutional interest"},
        "MORPHO": {"score": 78, "rationale": "Apollo investment, institutional curator standard"},
        "QNT": {"score": 72, "rationale": "Enterprise interoperability focus"},
        "XLM": {"score": 70, "rationale": "Payments infrastructure, enterprise partnerships"},
        "KAS": {"score": 50, "rationale": "Retail-driven, limited institutional adoption"},
        "AAVE": {"score": 75, "rationale": "SOC 2 compliance, Horizon RWA platform"},
        "SUI": {"score": 70, "rationale": "CME futures, multiple ETF filings"},
        "ONDO": {"score": 72, "rationale": "RWA focus, BlackRock BUIDL integration"},
        "TAO": {"score": 65, "rationale": "Grayscale ETF filing, DCG backing"},
        "PENDLE": {"score": 65, "rationale": "Institutional Citadels product"},
        "ENA": {"score": 60, "rationale": "Large USDe supply, institutional iUSDe"},
        "CANTON": {"score": 55, "rationale": "Enterprise blockchain, pre-market phase"},
    }
    return fallbacks.get(symbol, {"score": 55, "rationale": "Limited institutional presence"})


def score_revenue(symbol: str, name: str, use_cache: bool = True) -> dict:
    """
    Score revenue/fees using Claude when API data is unavailable.

    This is a fallback for when DefiLlama doesn't have revenue data.
    The score is marked as 'estimated' to indicate it's LLM-derived.

    Args:
        symbol: Asset symbol (e.g., 'LINK')
        name: Asset name (e.g., 'Chainlink')
        use_cache: Whether to use cached scores

    Returns:
        Dict with 'score' (int), 'rationale' (str), and 'estimated' (bool)
    """
    cache_key = f"revenue_{symbol}"

    if use_cache and cache_key in _score_cache:
        return _score_cache[cache_key]

    result = _query_claude(
        REVENUE_PROMPT.format(symbol=symbol, name=name), cache_key
    )

    if result:
        result["estimated"] = True
        _score_cache[cache_key] = result
        return result

    # Fallback scores based on known assets
    fallback = _get_fallback_revenue(symbol)
    fallback["estimated"] = True
    return fallback


def _get_fallback_revenue(symbol: str) -> dict:
    """Fallback revenue scores for known assets."""
    fallbacks = {
        "BTC": {"score": 75, "rationale": "Mining fees, ordinals revenue, strong network activity"},
        "ETH": {"score": 85, "rationale": "Transaction fees, MEV, blob fees, high network utilization"},
        "SOL": {"score": 82, "rationale": "High transaction volume, MEV revenue, growing DeFi fees"},
        "LINK": {"score": 72, "rationale": "Oracle data feed fees, CCIP cross-chain fees, growing enterprise adoption"},
        "XRP": {"score": 55, "rationale": "Minimal transaction fees by design, payment network model"},
        "AVAX": {"score": 68, "rationale": "Subnet fees, C-chain activity, moderate DeFi revenue"},
        "HBAR": {"score": 60, "rationale": "Enterprise transaction fees, consensus service revenue"},
        "HYPE": {"score": 88, "rationale": "Exchange fees, high trading volume, sustainable fee model"},
        "MORPHO": {"score": 75, "rationale": "Lending spreads, vault management fees, growing TVL"},
        "QNT": {"score": 50, "rationale": "Enterprise licensing model, limited on-chain fee activity"},
        "XLM": {"score": 45, "rationale": "Minimal fees by design for payments use case"},
        "KAS": {"score": 40, "rationale": "PoW chain with basic transaction fees, early stage"},
        "AAVE": {"score": 78, "rationale": "Interest spreads, flash loan fees, liquidation revenue"},
        "SUI": {"score": 65, "rationale": "Transaction fees, growing DeFi activity"},
        "ONDO": {"score": 60, "rationale": "RWA management fees, yield distribution"},
        "TAO": {"score": 45, "rationale": "Subnet registration fees, compute marketplace fees"},
        "PENDLE": {"score": 70, "rationale": "Yield trading fees, PT/YT swap fees"},
        "ENA": {"score": 65, "rationale": "Yield generation from staked assets, sUSDe fees"},
    }
    return fallbacks.get(symbol, {"score": 50, "rationale": "Limited revenue data available"})


def clear_cache():
    """Clear the score cache (call before weekly refresh)."""
    global _score_cache
    _score_cache = {}
