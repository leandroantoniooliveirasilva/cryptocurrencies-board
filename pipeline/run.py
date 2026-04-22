#!/usr/bin/env python3
"""
Weekly full scoring pipeline - all dimensions + Wyckoff phase detection.

This runs the complete scoring pipeline including:
- Qualitative scores (regulatory, institutional) via Claude API
- Revenue scores from DefiLlama
- Supply/on-chain analysis
- Wyckoff phase detection from price structure
- RSI calculation (daily/weekly)
- Macro filters (GLI, RS vs BTC, Fear & Greed)

Run weekly (Sunday 00:00 UTC) via cron.
For daily indicator updates, use: python -m pipeline.indicators

Usage:
    python -m pipeline.run
    python -m pipeline.run --dry-run
"""

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging
import os
import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from pipeline.category import (
    adoption_hint_for_category,
    resolve_asset_category,
    should_score_adoption_activity,
    should_score_value_capture,
    value_capture_skip_rationale,
)
from pipeline.config import config
from pipeline.fetchers import coingecko, defillama, fear_greed, gli, qualitative, relative_strength, supply
from pipeline.scoring import actions, composite, rsi, wyckoff
from pipeline.storage import migrations

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
ASSETS_FILE = REPO_ROOT / "pipeline" / "assets.yaml"
DB_PATH = REPO_ROOT / "pipeline" / "storage" / "history.sqlite"
PUBLIC_DIR = REPO_ROOT / "public"


def _aggregate_weekly_prices(
    dated_prices: list[tuple[date, float]]
) -> list[float]:
    """
    Aggregate dated daily prices into weekly closes by taking the last price
    of each ISO week.

    Uses the real date of each price (derived from the API timestamp) rather
    than assuming the last price is today's close, so gaps/lag in the upstream
    feed do not shift ISO-week boundaries.

    Args:
        dated_prices: List of (date, price) tuples (any order).

    Returns:
        List of weekly closing prices (oldest week to newest week).
    """
    if not dated_prices or len(dated_prices) < 7:
        return []

    # Group by ISO week (year, week_number) using the real date of each price.
    weeks: dict[tuple[int, int], tuple[date, float]] = {}
    for price_date, price in dated_prices:
        iso_year, iso_week, _ = price_date.isocalendar()
        week_key = (iso_year, iso_week)
        # Keep only the latest price within each ISO week.
        existing = weeks.get(week_key)
        if existing is None or price_date >= existing[0]:
            weeks[week_key] = (price_date, price)

    # Sort by ISO week key and return the closes.
    sorted_weeks = sorted(weeks.keys())
    return [weeks[week][1] for week in sorted_weeks]


def load_config() -> dict:
    """Load asset configuration from YAML.

    Returns the watchlist dict. This is deliberately distinct from the
    thresholds singleton imported at module level as ``config`` — do not
    reuse that name here to avoid shadowing bugs.
    """
    try:
        with open(ASSETS_FILE) as f:
            assets = yaml.safe_load(f)
            if not assets or not isinstance(assets, dict):
                logger.error(f"Invalid config in {ASSETS_FILE}: expected dict")
                return {"leaders": [], "runner_ups": [], "observation": []}
            return assets
    except FileNotFoundError:
        logger.error(f"Assets file not found: {ASSETS_FILE}")
        return {"leaders": [], "runner_ups": [], "observation": []}
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse {ASSETS_FILE}: {e}")
        return {"leaders": [], "runner_ups": [], "observation": []}


def compute_tier(composite_score: int) -> str:
    """
    Compute tier dynamically from composite score.

    Thresholds from config.yaml:
        - Leader:      composite >= 75
        - Runner-up:   composite >= 65
        - Observation: composite < 65
    """
    # Config loader guarantees tiers section exists; no fallback needed
    leader_threshold = config.tiers.leader
    runner_up_threshold = config.tiers.runner_up

    if composite_score >= leader_threshold:
        return "leader"
    elif composite_score >= runner_up_threshold:
        return "runner-up"
    else:
        return "observation"


def build_asset(entry: dict, conn, gli_downtrend: bool = False, fg_greedy: bool = False) -> dict:
    """
    Build complete asset data from config entry.
    Tier is computed dynamically from composite score.

    Args:
        entry: Asset config from YAML
        conn: Database connection
        gli_downtrend: True if Global Liquidity Index is contracting
        fg_greedy: True if Fear & Greed Index >= threshold (market greed)

    Returns:
        Complete asset dict for dashboard
    """
    symbol = entry["symbol"]
    name = entry["name"]
    asset_type = entry.get("asset_type", "smart-contract")  # Legacy label for discovery / display
    asset_category = resolve_asset_category(entry)
    weights_profile = composite.get_weights(asset_category)
    coingecko_id = entry.get("coingecko_id")
    defillama_slug = entry.get("defillama_slug")
    wyckoff_override = entry.get("wyckoff_override")
    fee_model = entry.get("fee_model")

    logger.info(f"Processing {symbol}...")

    # Fetch market data
    defi_data = defillama.fetch_defillama_data(defillama_slug)

    # Fetch daily prices for RSI from DefiLlama (free, no rate limits)
    # Days configured in config.yaml to ensure enough weekly data points
    data_cfg = config.data
    dated_prices = (
        defillama.fetch_daily_prices_with_timestamps(
            coingecko_id, days=data_cfg.price_history_days
        )
        if coingecko_id
        else None
    )
    # Convert to [(date, price)] using the real UTC timestamp from the API
    # so that ISO-week bucketing stays accurate even if the feed lags a day.
    dated_daily: list[tuple[date, float]] = []
    if dated_prices:
        for ts, price in dated_prices:
            price_date = datetime.fromtimestamp(ts, tz=timezone.utc).date()
            dated_daily.append((price_date, price))
    daily_prices = [price for _d, price in dated_daily]

    # For weekly RSI, group by ISO week and take last price of each week
    # This handles missing days and data gaps correctly
    weekly_prices = _aggregate_weekly_prices(dated_daily)

    rsi_period = config.rsi.period
    rsi_daily = rsi.compute_rsi(daily_prices, rsi_period) if len(daily_prices) >= data_cfg.min_daily_points else None
    rsi_weekly = rsi.compute_rsi(weekly_prices, rsi_period) if len(weekly_prices) >= data_cfg.min_weekly_points else None

    # Calculate weekly RSI from 4 weeks ago for slope check
    # This helps detect "first leg down" scenarios where weekly RSI is falling from elevated levels
    rsi_weekly_4w_ago = None
    if len(weekly_prices) >= data_cfg.min_weekly_points + 4:
        # Exclude the last 4 weekly prices to get RSI from ~4 weeks ago
        weekly_prices_4w_ago = weekly_prices[:-4]
        rsi_weekly_4w_ago = rsi.compute_rsi(weekly_prices_4w_ago, rsi_period)

    # Detect Wyckoff phase from price structure (or use manual override)
    if wyckoff_override:
        wyckoff_phase = wyckoff_override
        wyckoff_score = wyckoff.get_wyckoff_score(wyckoff_phase)
        wyckoff_rationale = f"Manual override: {wyckoff_override}"
    elif len(daily_prices) >= data_cfg.min_wyckoff_days:
        wyckoff_phase, wyckoff_score, wyckoff_rationale = wyckoff.detect_wyckoff_phase(daily_prices)
    else:
        wyckoff_phase = "Unknown"
        wyckoff_score = None  # Insufficient data - exclude from composite
        wyckoff_rationale = "Insufficient price data"

    cache_writes: list[tuple[str, str, int, str]] = []

    def record_cache_write(asset_symbol: str, score_type: str, score: int, rationale: str) -> None:
        cache_writes.append((asset_symbol, score_type, score, rationale))

    # Get qualitative scores (cached or fresh)
    cached_regulatory = migrations.get_cached_qualitative_score(conn, symbol, "regulatory")
    cached_institutional = migrations.get_cached_qualitative_score(conn, symbol, "institutional")

    if cached_regulatory:
        regulatory_data = cached_regulatory
    else:
        regulatory_data = qualitative.score_regulatory(symbol, name, use_cache=False)
        record_cache_write(symbol, "regulatory", regulatory_data["score"], regulatory_data["rationale"])

    if cached_institutional:
        institutional_data = cached_institutional
    else:
        institutional_data = qualitative.score_institutional(symbol, name, use_cache=False)
        record_cache_write(symbol, "institutional", institutional_data["score"], institutional_data["rationale"])

    # Value capture (category + fee_model gated)
    value_capture_score = None
    value_capture_estimated = False
    value_capture_rationale = None
    if not should_score_value_capture(weights_profile, fee_model):
        skip = value_capture_skip_rationale(fee_model)
        if skip:
            value_capture_rationale = skip
        else:
            value_capture_rationale = (
                "Value capture not in this category's weighted dimensions; weight redistributes."
            )
        logger.info(f"Skipping value capture for {symbol} (category/fee_model)")
    elif defi_data and defi_data.get("revenue_24h") is not None:
        revenue_24h = defi_data.get("revenue_24h")
        tvl = defi_data.get("tvl")
        fees_24h = defi_data.get("fees_24h")
        value_capture_score = defillama.compute_revenue_score(revenue_24h, tvl)
        value_capture_rationale = _build_revenue_rationale(
            revenue_24h, tvl, fees_24h, value_capture_score
        )
    else:
        logger.info(f"No API fee/revenue data for {symbol}, using LLM for value capture")
        cached_vc = migrations.get_cached_qualitative_score(conn, symbol, "value_capture")
        if not cached_vc:
            cached_vc = migrations.get_cached_qualitative_score(conn, symbol, "revenue")
        if cached_vc:
            vc_result = cached_vc
            value_capture_estimated = False
        else:
            vc_result = qualitative.score_value_capture(symbol, name, use_cache=False)
            record_cache_write(
                symbol, "value_capture",
                vc_result["score"], vc_result.get("rationale", "")
            )
            value_capture_estimated = vc_result.get("estimated", True)
        value_capture_score = vc_result.get("score")
        value_capture_rationale = vc_result.get(
            "rationale", "LLM-estimated value capture (no API data available)"
        )

    # Adoption / network activity (LLM, cached weekly)
    adoption_score = None
    adoption_rationale = None
    if should_score_adoption_activity(weights_profile):
        cached_ad = migrations.get_cached_qualitative_score(conn, symbol, "adoption_activity")
        if cached_ad:
            adoption_data = cached_ad
        else:
            hint = adoption_hint_for_category(asset_category)
            adoption_data = qualitative.score_adoption_activity(
                symbol, name, hint, use_cache=False
            )
            record_cache_write(
                symbol, "adoption_activity",
                adoption_data["score"], adoption_data.get("rationale", "")
            )
        adoption_score = adoption_data["score"]
        adoption_rationale = adoption_data.get("rationale", "")

    # Compute supply/on-chain score (AI-powered with data from CoinGecko)
    supply_data = supply.compute_supply_score(
        symbol=symbol,
        name=name,
        coingecko_id=coingecko_id,
        conn=conn,
        cache_writes=cache_writes,
        use_in_memory_cache=False,
    )
    supply_score = supply_data["score"]
    supply_rationale = supply_data["rationale"]

    # Wyckoff score already computed above from price data or manual override

    scores = {
        "institutional": institutional_data["score"],
        "adoption_activity": adoption_score,
        "value_capture": value_capture_score,
        "regulatory": regulatory_data["score"],
        "supply": supply_score,
        "wyckoff": wyckoff_score,
    }

    composite_score, missing_dimensions = composite.compute_composite(
        scores, asset_category=asset_category
    )

    # Compute tier dynamically from composite score
    tier = compute_tier(composite_score)

    # Get historical data for trends (weekly snapshots accumulate over time)
    # trend_7d = last 7 weekly snapshots (~7 weeks)
    # trend_30d = last 12 weekly snapshots (~12 weeks = quarter)
    # Note: Variable name is historical; represents quarterly trend, not 30 days
    trend_7d = migrations.get_trend_data(conn, symbol, 7)
    trend_30d = migrations.get_trend_data(conn, symbol, 12)
    composite_last_week = migrations.get_composite_last_week(conn, symbol)

    # Get weekly composite averages for stand-aside detection
    # This handles multiple runs per week during calibration by averaging snapshots
    weekly_averages = migrations.get_weekly_composite_averages(conn, symbol, weeks=10)

    # Add current score to trends if we have history
    if trend_7d:
        trend_7d.append(composite_score)
    else:
        trend_7d = [composite_score]

    if trend_30d:
        trend_30d.append(composite_score)
    else:
        trend_30d = [composite_score]

    # Calculate Relative Strength vs BTC
    rs_data = relative_strength.compute_relative_strength(dated_prices, symbol)
    rs_underperforming = rs_data["underperforming"]

    # Derive action (with GLI macro filter, RS filter, and weekly RSI slope check)
    # Use explicit None check: composite can legitimately be 0 for an asset
    # whose every dimension collapses, and `or` would silently replace it.
    effective_last_week = (
        composite_last_week if composite_last_week is not None else composite_score
    )
    action, decision_trace = actions.derive_action(
        composite=composite_score,
        composite_last_week=effective_last_week,
        tier=tier,
        wyckoff_phase=wyckoff_phase,
        trend_7d=trend_7d,
        trend_30d=trend_30d,
        rsi_daily=rsi_daily,
        rsi_weekly=rsi_weekly,
        rsi_weekly_4w_ago=rsi_weekly_4w_ago,
        gli_downtrend=gli_downtrend,
        rs_underperforming=rs_underperforming,
        fg_greedy=fg_greedy,
        weekly_averages=weekly_averages,
    )

    # Get action metadata
    label_changed_days_ago = migrations.get_label_changed_days_ago(conn, symbol)
    strong_accumulate_days = migrations.get_strong_accumulate_days(conn, symbol)

    # Build note
    note = _build_note(symbol, asset_type, regulatory_data, institutional_data, wyckoff_phase)

    weights = composite.get_weights(asset_category)

    note_detailed = _build_detailed_reasoning(
        symbol=symbol,
        name=name,
        tier=tier,
        asset_type=asset_type,
        asset_category=asset_category,
        scores=scores,
        weights=weights,
        composite=composite_score,
        regulatory=regulatory_data,
        institutional=institutional_data,
        wyckoff_phase=wyckoff_phase,
        action=action,
        rsi_daily=rsi_daily,
        rsi_weekly=rsi_weekly,
        rs_data=rs_data,
        value_capture_estimated=value_capture_estimated,
        decision_trace=decision_trace,
        wyckoff_rationale=wyckoff_rationale,
    )

    score_rationales = {
        "institutional": institutional_data["rationale"],
        "regulatory": regulatory_data["rationale"],
        "supply": supply_rationale,
        "wyckoff": wyckoff_rationale,
    }
    if adoption_rationale is not None:
        score_rationales["adoption_activity"] = adoption_rationale
    if value_capture_rationale is not None:
        score_rationales["value_capture"] = value_capture_rationale

    return {
        "symbol": symbol,
        "name": name,
        "tier": tier,
        "asset_type": asset_type,
        "asset_category": asset_category,
        "scores": scores,
        "score_rationales": score_rationales,
        "weights": weights,
        "composite": composite_score,
        "composite_last_week": effective_last_week,
        "wyckoff_phase": wyckoff_phase,
        "trend": trend_7d[-7:],  # Last 7 days
        "trend_30d": trend_30d[-30:],  # Last 30 days
        "rsi_daily": rsi_daily,
        "rsi_weekly": rsi_weekly,
        "action": action,
        "decision_trace": decision_trace,
        "strong_accumulate_days_active": strong_accumulate_days + (1 if action == "strong-accumulate" else 0),
        "label_changed_days_ago": label_changed_days_ago,
        "missing_dimensions": missing_dimensions,
        "value_capture_estimated": value_capture_estimated,
        "revenue_estimated": value_capture_estimated,
        "rs_vs_btc": {
            "underperforming": rs_data["underperforming"],
            "change_pct": rs_data["rs_change_pct"],
        },
        "note": note,
        "note_detailed": note_detailed,
        "cache_writes": cache_writes,
    }


def _get_max_workers(default_workers: int = 4) -> int:
    raw_value = os.environ.get("PIPELINE_MAX_WORKERS")
    if not raw_value:
        return default_workers
    try:
        parsed = int(raw_value)
        return max(1, parsed)
    except ValueError:
        logger.warning(f"Invalid PIPELINE_MAX_WORKERS={raw_value!r}, using {default_workers}")
        return default_workers


def _build_asset_worker(entry: dict, gli_downtrend: bool, fg_greedy: bool) -> dict:
    symbol = entry.get("symbol", "unknown")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA busy_timeout = 60000')
    try:
        asset = build_asset(entry, conn, gli_downtrend=gli_downtrend, fg_greedy=fg_greedy)
        return {"symbol": symbol, "asset": asset, "error": None}
    except Exception as e:
        return {"symbol": symbol, "asset": None, "error": str(e)}
    finally:
        conn.close()




def _build_revenue_rationale(
    revenue_24h: float,
    tvl: float,
    fees_24h: float,
    score: int,
) -> str:
    """
    Build evidence-backed rationale for revenue score from DefiLlama data.

    Args:
        revenue_24h: Daily protocol revenue in USD
        tvl: Total value locked in USD (or None for oracles/infra)
        fees_24h: Daily fees in USD (may equal revenue for some protocols)
        score: The computed revenue score

    Returns:
        Rationale string with actual data backing the score
    """
    annual_revenue = revenue_24h * 365

    # Format large numbers for readability
    def fmt(n):
        if n >= 1_000_000_000:
            return f"${n/1e9:.2f}B"
        elif n >= 1_000_000:
            return f"${n/1e6:.1f}M"
        elif n >= 1_000:
            return f"${n/1e3:.0f}K"
        else:
            return f"${n:.0f}"

    parts = [f"Daily revenue: {fmt(revenue_24h)} (~{fmt(annual_revenue)}/year)"]

    if tvl and tvl > 0:
        ratio = annual_revenue / tvl * 100
        parts.append(f"TVL: {fmt(tvl)}")
        parts.append(f"Revenue/TVL ratio: {ratio:.2f}%")
    else:
        parts.append("No TVL (oracle/infra model, scored on absolute revenue)")

    if fees_24h and fees_24h != revenue_24h:
        parts.append(f"Daily fees: {fmt(fees_24h)}")

    return ". ".join(parts) + "."


def _build_note(
    symbol: str,
    asset_type: str,
    regulatory: dict,
    institutional: dict,
    wyckoff_phase: str
) -> str:
    """Build concise note for asset card."""
    notes = []

    # Highlight strongest dimension
    if institutional["score"] >= 85:
        notes.append("Strong institutional adoption")
    if regulatory["score"] >= 85:
        notes.append("Regulatory clarity")

    # Add Wyckoff context
    # Use precise phase tokens to avoid matching stray 'c' in "accumulation"
    phase_lower = wyckoff_phase.lower() if wyckoff_phase else ""
    is_distribution = "distribution" in phase_lower
    is_spring_zone = (not is_distribution) and (
        "phase c" in phase_lower
        or "→c" in phase_lower
        or "->c" in phase_lower
    )
    if is_spring_zone:
        notes.append("Wyckoff spring zone")
    elif is_distribution:
        notes.append("Distribution risk")

    if notes:
        return ". ".join(notes)

    # Default notes by asset type and symbol
    type_notes = {
        "store-of-value": "Store of value, supply-focused",
        "smart-contract": "Smart contract platform",
        "defi": "DeFi protocol, revenue-focused",
        "infrastructure": "Infrastructure/enterprise",
    }

    symbol_notes = {
        "BTC": "Market leader, benchmark asset",
        "SOL": "High-throughput L1, DeFi ecosystem",
        "LINK": "Oracle infrastructure standard",
        "HYPE": "Revenue-per-user sector leader",
        "QNT": "Enterprise interoperability",
        "XRP": "Cross-border payments",
        "AVAX": "Subnet architecture",
    }

    return symbol_notes.get(symbol, type_notes.get(asset_type, "Monitoring framework signals"))


def _build_detailed_reasoning(
    symbol: str,
    name: str,
    tier: str,
    asset_type: str,
    asset_category: str,
    scores: dict,
    weights: dict,
    composite: int,
    regulatory: dict,
    institutional: dict,
    wyckoff_phase: str,
    action: str,
    rsi_daily,  # float or None
    rsi_weekly,  # float or None
    rs_data: dict = None,  # Relative strength vs BTC data
    value_capture_estimated: bool = False,
    decision_trace: dict = None,
    wyckoff_rationale: str = '',
) -> str:
    """
    Build detailed reasoning explaining why this asset is on the list,
    its tier placement, dimension scores, and investment thesis.
    """
    lines = []

    # 1. Tier explanation
    tier_explanations = {
        "leader": f"{symbol} holds Leader status in the framework, representing highest-conviction assets with established track records. Leaders receive priority for accumulation when conditions align.",
        "runner-up": f"{symbol} is classified as Runner-up, showing strong fundamentals but requiring additional confirmation before potential promotion to Leader tier. These assets are monitored for breakout signals.",
        "observation": f"{symbol} sits in the Observation tier, meaning it's being tracked for research purposes but doesn't yet warrant position sizing. The framework monitors for improving metrics.",
    }
    lines.append(tier_explanations.get(tier, f"{symbol} is tracked in the {tier} tier."))

    category_context = {
        "monetary-store-of-value": "Category: monetary store of value — institutional + supply/security + regulatory; no separate value-capture dimension.",
        "smart-contract-platform": "Category: smart-contract platform — balanced institutional, adoption, value capture, supply, regulatory.",
        "defi-protocol": "Category: DeFi protocol — value capture and adoption weighted alongside institutions and supply.",
        "oracle-data": "Category: oracle/data — adoption (e.g. TVS) and institutions weighted with value capture and supply.",
        "enterprise-settlement": "Category: enterprise settlement — adoption and regulatory emphasis; burn/mint in supply.",
        "payments-rail": "Category: payments rail — institutions and regulatory; no value capture by design.",
        "shared-security": "Category: shared security / restaking — adoption and value capture central.",
        "data-availability-modular": "Category: modular data availability — adoption and value capture with supply.",
        "ai-compute-depin": "Category: AI / DePIN — adoption and value capture with supply and regulatory.",
        "default": f"Asset category: {asset_category}.",
    }
    lines.append(category_context.get(asset_category, category_context["default"]))

    # 3. Dimension breakdown
    lines.append("")
    lines.append("DIMENSION BREAKDOWN:")

    # Institutional
    inst_score = scores.get("institutional", 0)
    inst_weight = weights.get("institutional", 0)
    inst_rationale = institutional.get("rationale", "")
    if inst_score >= 85:
        inst_level = "Excellent"
    elif inst_score >= 70:
        inst_level = "Strong"
    elif inst_score >= 50:
        inst_level = "Moderate"
    else:
        inst_level = "Limited"
    lines.append(f"• Institutional ({inst_score}/100, {int(inst_weight*100)}% weight): {inst_level} institutional presence. {inst_rationale}")

    # Regulatory
    reg_score = scores.get("regulatory", 0)
    reg_weight = weights.get("regulatory", 0)
    reg_rationale = regulatory.get("rationale", "")
    if reg_score >= 85:
        reg_level = "Clear"
    elif reg_score >= 70:
        reg_level = "Favorable"
    elif reg_score >= 50:
        reg_level = "Uncertain"
    else:
        reg_level = "Concerning"
    lines.append(f"• Regulatory ({reg_score}/100, {int(reg_weight*100)}% weight): {reg_level} regulatory standing. {reg_rationale}")

    # Supply
    supply_score = scores.get("supply", 0)
    supply_weight = weights.get("supply", 0)
    if supply_score >= 80:
        supply_desc = "Healthy on-chain metrics with favorable supply distribution and accumulation patterns."
    elif supply_score >= 60:
        supply_desc = "Acceptable supply dynamics with some concentration or distribution concerns."
    else:
        supply_desc = "Supply metrics warrant caution—potential concentration or unfavorable distribution."
    lines.append(f"• Supply/On-Chain ({supply_score}/100, {int(supply_weight*100)}% weight): {supply_desc}")

    # Adoption / value capture (only when weighted)
    ad_score = scores.get("adoption_activity")
    ad_weight = weights.get("adoption_activity", 0)
    if ad_weight and ad_score is not None:
        lines.append(
            f"• Adoption / activity ({ad_score}/100, {int(ad_weight * 100)}% weight): "
            f"Network usage and growth signals for this category."
        )

    vc_score = scores.get("value_capture")
    vc_weight = weights.get("value_capture", 0)
    if vc_weight and vc_score is not None:
        if vc_score >= 80:
            vc_desc = "Strong holder-accruing economics."
        elif vc_score >= 50:
            vc_desc = "Moderate value capture; typical for growth-phase protocols."
        else:
            vc_desc = "Limited value capture—may rely on incentives or early-stage economics."
        est_tag = " ⚠️ ESTIMATED" if value_capture_estimated else ""
        lines.append(
            f"• Value capture ({vc_score}/100, {int(vc_weight * 100)}% weight{est_tag}): {vc_desc}"
        )
        if value_capture_estimated:
            lines.append("  (Score derived from LLM research — API data unavailable)")
    elif vc_weight and vc_score is None:
        lines.append("• Value capture (N/A, excluded): Not scored for this category or fee model.")

    # 4. Wyckoff phase context (for stand-aside logic)
    phase_lower = wyckoff_phase.lower() if wyckoff_phase else ""
    is_distribution = "distribution" in phase_lower

    # 6. RSI context
    if rsi_daily is not None or rsi_weekly is not None:
        lines.append("")
        lines.append("RSI CONTEXT:")
        if rsi_daily is not None:
            if rsi_daily <= 30:
                rsi_d_desc = f"Daily RSI at {rsi_daily:.1f} indicates oversold conditions—potential short-term bounce zone."
            elif rsi_daily >= 70:
                rsi_d_desc = f"Daily RSI at {rsi_daily:.1f} signals overbought territory—momentum extended."
            else:
                rsi_d_desc = f"Daily RSI at {rsi_daily:.1f} sits in neutral range."
            lines.append(f"• {rsi_d_desc}")
        if rsi_weekly is not None:
            if rsi_weekly <= 35:
                rsi_w_desc = f"Weekly RSI at {rsi_weekly:.1f} suggests longer-term oversold conditions—structural opportunity if fundamentals hold."
            elif rsi_weekly >= 70:
                rsi_w_desc = f"Weekly RSI at {rsi_weekly:.1f} indicates elevated momentum on higher timeframe."
            else:
                rsi_w_desc = f"Weekly RSI at {rsi_weekly:.1f} remains in healthy range."
            lines.append(f"• {rsi_w_desc}")

    # 7. Relative Strength vs BTC
    if rs_data and symbol.upper() != "BTC":
        rs_change = rs_data.get("rs_change_pct")
        rs_underperforming = rs_data.get("underperforming", False)
        if rs_change is not None:
            lines.append("")
            lines.append("RELATIVE STRENGTH vs BTC:")
            change_pct = rs_change * 100
            if rs_underperforming:
                lines.append(f"• ⚠️ CAUTION: Underperforming BTC by {abs(change_pct):.1f}% over {config.rs.lookback_days} days. Consider whether BTC itself may be a better allocation.")
            elif change_pct > 0:
                lines.append(f"• Outperforming BTC by {change_pct:.1f}% over {config.rs.lookback_days} days—relative strength is favorable.")
            else:
                lines.append(f"• Slight underperformance vs BTC ({change_pct:.1f}% over {config.rs.lookback_days} days) but within tolerance.")

    # 8. Action reasoning
    lines.append("")
    lines.append("CURRENT ACTION:")
    # Build stand-aside reason based on actual trigger (distribution vs sharp decline)
    if action == 'stand-aside' and is_distribution:
        stand_aside_reason = "STAND ASIDE is active due to distribution phase detection. Capital preservation takes priority."
    else:
        stand_aside_reason = "STAND ASIDE is active due to sharp composite decline. This may be a temporary pullback, but capital preservation takes priority until structure stabilizes."

    action_reasoning = {
        "strong-accumulate": f"STRONG ACCUMULATE is firing because daily RSI shows a short-term oversold flush while weekly RSI and composite score remain healthy. This dislocation within an otherwise solid structure represents a high-conviction entry window.",
        "accumulate": f"ACCUMULATE status indicates this Leader-tier asset meets tranche-building criteria: composite above threshold, favorable Wyckoff phase, and RSI not overbought. Systematic position building is appropriate.",
        "promote": f"PROMOTE CANDIDATE status signals this Runner-up is demonstrating Leader-quality metrics. Manual review recommended for potential tier promotion.",
        "hold": f"HOLD status indicates the position is active with no current add or trim signals. Current allocation is appropriate—patience is the strategy.",
        "await": f"AWAIT status means signals are building but not yet confirmed. The asset shows promise but hasn't crossed activation thresholds.",
        "observe": f"OBSERVE status reflects Observation-tier placement—tracked for research, not positioned. No action required.",
        "stand-aside": stand_aside_reason,
    }
    if decision_trace and decision_trace.get("summary"):
        lines.append(decision_trace["summary"])
    else:
        lines.append(action_reasoning.get(action, f"Current action: {action}"))

    if decision_trace:
        lines.append("")
        lines.append("DECISION TRACE:")
        lines.append(f"• path: {_trace_path_label(decision_trace.get('path', ''))}")
        if decision_trace.get("base_action") is not None:
            lines.append(
                f"• base_action: {_action_label(decision_trace['base_action'])}"
            )
        lines.append(
            f"• final_action: {_action_label(decision_trace.get('final_action', action))}"
        )
        dg = decision_trace.get("downgrades") or {}
        if dg:
            reasons = dg.get("reasons") or []
            lines.append(
                f"• downgrades: levels_applied={dg.get('levels_applied')}, "
                f"macro_levels={dg.get('macro_levels')}, wyckoff_levels={dg.get('wyckoff_levels')}"
            )
            if reasons:
                lines.append(
                    f"• downgrade_reasons: {', '.join(_downgrade_reason_label(r) for r in reasons)}"
                )

    # 9. Composite summary
    lines.append("")
    lines.append(f"COMPOSITE SCORE: {composite}/100")
    if composite >= 75:
        lines.append("This places the asset in the top tier of framework scoring, indicating strong alignment across weighted dimensions.")
    elif composite >= 65:
        lines.append("This score reflects solid fundamentals with room for improvement in specific dimensions.")
    else:
        lines.append("This score indicates the asset is being monitored but hasn't yet reached high-conviction thresholds.")

    return "\n".join(lines)


def _trace_path_label(path: str) -> str:
    labels = {
        'leader_capitulation_both_rsi': 'Leader capitulation (weekly + daily RSI)',
        'leader_capitulation_weekly_only': 'Leader capitulation (weekly RSI only)',
        'leader_wyckoff_weekly_slope_downgrade': 'Leader Wyckoff setup reduced by weekly RSI slope',
        'leader_wyckoff_strong_accumulate': 'Leader strong-accumulate Wyckoff setup',
        'leader_wyckoff_accumulate': 'Leader accumulate Wyckoff setup',
        'leader_hold_default': 'Leader hold default',
        'runner_up_promote': 'Runner-up promote',
        'runner_up_await': 'Runner-up await',
        'observe_default': 'Observation default',
        'stand_aside_sharp_decline': 'Stand aside from sharp decline',
    }
    return labels.get(path, path.replace('_', ' '))


def _action_label(action: str) -> str:
    labels = {
        'strong-accumulate': 'Strong Accumulate',
        'accumulate': 'Accumulate',
        'hold': 'Hold',
        'await': 'Await Confirmation',
        'promote': 'Promote Candidate',
        'observe': 'Observe',
        'stand-aside': 'Stand Aside',
    }
    return labels.get(action, action)


def _downgrade_reason_label(reason: str) -> str:
    labels = {
        'macro:gli_contracting': 'Global liquidity contracting',
        'macro:rs_underperforming_btc': 'Relative strength underperforming BTC',
        'macro:fear_greed_euphoria': 'Fear & Greed in euphoria zone',
        'wyckoff:markup': 'Wyckoff in markup (late-cycle entry risk)',
        'wyckoff:distribution_or_markdown': 'Wyckoff in distribution/markdown (risk-off structure)',
    }
    return labels.get(reason, reason)


def write_output(output: dict, dry_run: bool = False) -> None:
    """Write output files."""
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    latest_path = PUBLIC_DIR / "latest.json"

    if dry_run:
        logger.info("DRY RUN - would write to:")
        logger.info(f"  {latest_path}")
        logger.info(f"Output preview:\n{json.dumps(output, indent=2)[:2000]}...")
        return

    with open(latest_path, "w") as f:
        json.dump(output, f, indent=2)
    logger.info(f"Wrote {latest_path}")


def main():
    parser = argparse.ArgumentParser(description="Run weekly scoring pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Don't write output files")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Weekly full scoring pipeline")
    logger.info("=" * 60)

    # Load asset definitions (flat list - tiers computed dynamically)
    assets_config = load_config()
    assets_list = assets_config.get("assets", [])
    # Fallback for old tiered format
    if not assets_list:
        assets_list = (
            assets_config.get("leaders", []) +
            assets_config.get("runner_ups", []) +
            assets_config.get("observation", [])
        )
    logger.info(f"Loaded {len(assets_list)} assets from config")

    # Fetch Global Liquidity Index status (macro filter)
    gli_data = gli.fetch_gli_data()
    gli_downtrend = gli_data["downtrend"]
    if gli_data["source"] != "fallback":
        gli_trend = gli.get_gli_trend_label(gli_data)
        logger.info(f"GLI status: {gli_trend} (source: {gli_data['source']})")
    else:
        logger.info("GLI data unavailable - macro filter disabled")

    # Fetch Fear & Greed Index (sentiment filter)
    fg_data = fear_greed.fetch_fear_greed()
    fg_greedy = fg_data.get("greedy", False)
    if fg_data.get("enabled") and fg_data.get("value") is not None:
        logger.info(f"Fear & Greed: {fg_data['value']} ({fg_data['classification']}) - {'GREEDY' if fg_greedy else 'neutral'}")
    else:
        logger.info("Fear & Greed data unavailable - sentiment filter disabled")

    # Fetch global market data (BTC dominance, stablecoin supply)
    global_market = coingecko.fetch_global_market_data()
    stablecoin_mcap = coingecko.fetch_stablecoin_mcap()
    if global_market.get("btc_dominance"):
        logger.info(f"BTC dominance: {global_market['btc_dominance']}%")
    if stablecoin_mcap:
        logger.info(f"Stablecoin market cap: ${stablecoin_mcap/1e9:.1f}B")

    # Clear RS cache for fresh BTC price data
    relative_strength.clear_cache()
    if config.rs.enabled:
        logger.info(f"RS filter enabled: {config.rs.lookback_days}d lookback, {config.rs.underperformance_threshold*100:.0f}% threshold")

    # Initialize database
    conn = migrations.init_db(DB_PATH)
    today = date.today().isoformat()

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_date": today,
        "framework_version": "3.0",
        "weight_profiles": composite.WEIGHTS_BY_TYPE,
        "thresholds": {
            "min_display_score": config.composite.min_display_score,
            "stale_hours": config.display.stale_hours,
            "rsi": {
                "overbought": config.rsi.overbought_weekly,
                "oversold": config.rsi.oversold_daily,
                "capitulation": config.rsi.capitulation_weekly,
            },
        },
        "gli": {
            "enabled": config.gli.enabled,
            "downtrend": gli_downtrend,
            "trend": gli_data.get("trend", gli.get_gli_trend_label(gli_data)),
            "current": gli_data["current"],
            "offset_value": gli_data["offset_value"],
            "offset_days": gli_data["offset_days"],
            "source": gli_data["source"],
            "current_obs_date": gli_data.get("current_obs_date"),
            "offset_obs_date": gli_data.get("offset_obs_date"),
            "component_coverage": gli_data.get("component_coverage"),
            "components_used": gli_data.get("components_used", []),
            "components_missing": gli_data.get("components_missing", []),
        },
        "rs": {
            "enabled": config.rs.enabled,
            "lookback_days": config.rs.lookback_days,
            "threshold_pct": config.rs.underperformance_threshold * 100,
        },
        "fear_greed": {
            "enabled": fg_data.get("enabled", False),
            "value": fg_data.get("value"),
            "classification": fg_data.get("classification"),
            "threshold": fg_data.get("threshold", 70),
            "greedy": fg_greedy,
        },
        "market_context": {
            "btc_dominance": global_market.get("btc_dominance"),
            "stablecoin_mcap_billions": round(stablecoin_mcap / 1e9, 1) if stablecoin_mcap else None,
            "total_mcap_trillions": round(global_market.get("total_mcap", 0) / 1e12, 2) if global_market.get("total_mcap") else None,
        },
        "assets": [],
    }

    # Process all assets (tiers computed dynamically from composite scores)
    logger.info(f"\nProcessing {len(assets_list)} assets...")
    worker_count = min(_get_max_workers(), max(1, len(assets_list)))
    logger.info(f"Parallel workers: {worker_count}")

    processed_assets: list[dict] = []
    if worker_count == 1:
        for entry in assets_list:
            result = _build_asset_worker(entry, gli_downtrend=gli_downtrend, fg_greedy=fg_greedy)
            if result["error"]:
                logger.error(f"  Failed to process {result['symbol']}: {result['error']}")
                continue
            processed_assets.append(result["asset"])
    else:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(_build_asset_worker, entry, gli_downtrend, fg_greedy): entry
                for entry in assets_list
            }
            for future in as_completed(futures):
                result = future.result()
                if result["error"]:
                    logger.error(f"  Failed to process {result['symbol']}: {result['error']}")
                    continue
                processed_assets.append(result["asset"])

    # Persist cache writes and snapshots in the master process only.
    for asset in processed_assets:
        if not args.dry_run:
            for symbol, score_type, score, rationale in asset.get("cache_writes", []):
                migrations.save_qualitative_score(conn, symbol, score_type, score, rationale)
            migrations.save_snapshot(conn, asset, today)

        asset.pop("cache_writes", None)
        output["assets"].append(asset)
        logger.info(
            f"  {asset['symbol']} ({asset['tier']}): composite={asset['composite']}, action={asset['action']}"
        )

    # Sort assets by tier priority then composite score
    tier_order = {"leader": 0, "runner-up": 1, "observation": 2}
    output["assets"].sort(key=lambda a: (tier_order.get(a["tier"], 3), -a["composite"]))

    # Commit database changes only when writes are enabled.
    if not args.dry_run:
        conn.commit()
    conn.close()

    # Write output
    write_output(output, dry_run=args.dry_run)

    logger.info("\n" + "=" * 60)
    logger.info(f"Pipeline complete. Processed {len(output['assets'])} assets.")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
