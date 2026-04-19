#!/usr/bin/env python3
"""
Pipeline orchestrator - daily scoring scan.

Usage:
    python -m pipeline.run
    python -m pipeline.run --dry-run
"""

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

import argparse
import json
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from pipeline.config import config
from pipeline.fetchers import defillama, gli, qualitative, relative_strength, supply
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
        - Runner-up:   composite >= 55
        - Observation: composite < 55
    """
    leader_threshold = getattr(config, 'tiers', None)
    if leader_threshold:
        leader_threshold = config.tiers.leader
        runner_up_threshold = config.tiers.runner_up
    else:
        # Fallback defaults
        leader_threshold = 75
        runner_up_threshold = 55

    if composite_score >= leader_threshold:
        return "leader"
    elif composite_score >= runner_up_threshold:
        return "runner-up"
    else:
        return "observation"


def build_asset(entry: dict, conn, gli_downtrend: bool = False) -> dict:
    """
    Build complete asset data from config entry.
    Tier is computed dynamically from composite score.

    Args:
        entry: Asset config from YAML
        conn: Database connection
        gli_downtrend: True if Global Liquidity Index is contracting

    Returns:
        Complete asset dict for dashboard
    """
    symbol = entry["symbol"]
    name = entry["name"]
    asset_type = entry.get("asset_type", "smart-contract")  # Default to balanced
    coingecko_id = entry.get("coingecko_id")
    defillama_slug = entry.get("defillama_slug")
    wyckoff_override = entry.get("wyckoff_override")

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
    elif len(daily_prices) >= data_cfg.min_wyckoff_days:
        wyckoff_phase, wyckoff_score = wyckoff.detect_wyckoff_phase(daily_prices)
    else:
        wyckoff_phase = "Unknown"
        wyckoff_score = None  # Insufficient data - exclude from composite

    # Get qualitative scores (cached or fresh)
    cached_regulatory = migrations.get_cached_qualitative_score(conn, symbol, "regulatory")
    cached_institutional = migrations.get_cached_qualitative_score(conn, symbol, "institutional")

    if cached_regulatory:
        regulatory_data = cached_regulatory
    else:
        regulatory_data = qualitative.score_regulatory(symbol, name)
        migrations.save_qualitative_score(
            conn, symbol, "regulatory",
            regulatory_data["score"], regulatory_data["rationale"]
        )

    if cached_institutional:
        institutional_data = cached_institutional
    else:
        institutional_data = qualitative.score_institutional(symbol, name)
        migrations.save_qualitative_score(
            conn, symbol, "institutional",
            institutional_data["score"], institutional_data["rationale"]
        )

    # Compute revenue score (None if data unavailable)
    revenue_score = None
    if defi_data and defi_data.get("revenue_24h") is not None:
        revenue_score = defillama.compute_revenue_score(
            defi_data.get("revenue_24h"),
            defi_data.get("tvl")
        )

    # Compute supply/on-chain score (AI-powered with data from CoinGecko)
    supply_score = supply.compute_supply_score(
        symbol=symbol,
        name=name,
        coingecko_id=coingecko_id,
        conn=conn,
    )

    # Wyckoff score already computed above from price data or manual override

    # Build scores dict with all 5 dimensions
    scores = {
        "institutional": institutional_data["score"],
        "revenue": revenue_score,
        "regulatory": regulatory_data["score"],
        "supply": supply_score,
        "wyckoff": wyckoff_score,
    }

    # Compute composite with asset-type-specific weights
    # Returns (score, missing_count) - missing dimensions are excluded from calculation
    composite_score, missing_dimensions = composite.compute_composite(scores, asset_type=asset_type)

    # Compute tier dynamically from composite score
    tier = compute_tier(composite_score)

    # Get historical data for trends
    trend_7d = migrations.get_trend_data(conn, symbol, 7)
    trend_30d = migrations.get_trend_data(conn, symbol, 30)
    composite_last_week = migrations.get_composite_last_week(conn, symbol)

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
    action = actions.derive_action(
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
    )

    # Get action metadata
    label_changed_days_ago = migrations.get_label_changed_days_ago(conn, symbol)
    strong_accumulate_days = migrations.get_strong_accumulate_days(conn, symbol)

    # Build note
    note = _build_note(symbol, asset_type, regulatory_data, institutional_data, wyckoff_phase)

    # Get weight profile for this asset type
    weights = composite.get_weights(asset_type)

    # Build detailed reasoning for modal view
    note_detailed = _build_detailed_reasoning(
        symbol=symbol,
        name=name,
        tier=tier,
        asset_type=asset_type,
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
    )

    return {
        "symbol": symbol,
        "name": name,
        "tier": tier,
        "asset_type": asset_type,
        "scores": scores,
        "weights": weights,
        "composite": composite_score,
        "composite_last_week": effective_last_week,
        "wyckoff_phase": wyckoff_phase,
        "trend": trend_7d[-7:],  # Last 7 days
        "trend_30d": trend_30d[-30:],  # Last 30 days
        "rsi_daily": rsi_daily,
        "rsi_weekly": rsi_weekly,
        "action": action,
        "strong_accumulate_days_active": strong_accumulate_days + (1 if action == "strong-accumulate" else 0),
        "label_changed_days_ago": label_changed_days_ago,
        "missing_dimensions": missing_dimensions,
        "rs_vs_btc": {
            "underperforming": rs_data["underperforming"],
            "change_pct": rs_data["rs_change_pct"],
        },
        "note": note,
        "note_detailed": note_detailed,
    }




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

    # 2. Asset type context
    type_context = {
        "store-of-value": "As a store-of-value asset, the scoring heavily weights institutional adoption (40%) and supply dynamics (25%), with less emphasis on protocol revenue.",
        "smart-contract": "As a smart-contract platform, the scoring balances institutional backing (30%), revenue generation (25%), and supply health (20%) to capture both adoption and sustainability.",
        "defi": "As a DeFi protocol, revenue and fee generation dominates the scoring (35%), reflecting the importance of sustainable tokenomics in this sector.",
        "infrastructure": "As an infrastructure asset, institutional adoption (35%) and regulatory clarity (25%) are prioritized, reflecting enterprise deployment requirements.",
    }
    lines.append(type_context.get(asset_type, ""))

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

    # Revenue
    rev_score = scores.get("revenue")
    rev_weight = weights.get("revenue", 0)
    if rev_score is not None:
        if rev_score >= 80:
            rev_desc = "Strong fee generation indicating sustainable protocol economics."
        elif rev_score >= 50:
            rev_desc = "Moderate revenue, typical for growth-phase protocols."
        else:
            rev_desc = "Limited fee revenue—protocol may rely on token incentives or is early-stage."
        lines.append(f"• Revenue/Fees ({rev_score}/100, {int(rev_weight*100)}% weight): {rev_desc}")
    else:
        lines.append(f"• Revenue/Fees (N/A, excluded): No protocol revenue data available for this asset type.")

    # Wyckoff
    wyck_score = scores.get("wyckoff")
    wyck_weight = weights.get("wyckoff", 0)
    phase_lower = wyckoff_phase.lower() if wyckoff_phase else ""
    is_distribution = "distribution" in phase_lower
    is_bullish_phase = (not is_distribution) and (
        "accumulation" in phase_lower
        or "phase c" in phase_lower
        or "b→c" in phase_lower
        or "b->c" in phase_lower
    )
    if wyck_score is not None:
        if is_bullish_phase:
            wyck_desc = f"Currently in {wyckoff_phase}—historically favorable for position building as price structure suggests markup potential."
        elif is_distribution:
            wyck_desc = f"Currently in {wyckoff_phase}—caution warranted as price structure suggests potential markdown phase ahead."
        elif "markup" in phase_lower:
            wyck_desc = f"Currently in {wyckoff_phase}—trend is favorable but entries should be measured as some move has already occurred."
        else:
            wyck_desc = f"Currently in {wyckoff_phase}. Technical structure is being monitored for clearer phase identification."
        lines.append(f"• Wyckoff ({wyck_score}/100, {int(wyck_weight*100)}% weight): {wyck_desc}")
    else:
        lines.append(f"• Wyckoff (N/A, excluded): Insufficient price data for Wyckoff phase detection.")

    # 4. RSI context
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

    # 5. Relative Strength vs BTC
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

    # 6. Action reasoning
    lines.append("")
    lines.append("CURRENT ACTION:")
    # Build stand-aside reason based on actual trigger (distribution vs sharp decline)
    if is_distribution:
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
    lines.append(action_reasoning.get(action, f"Current action: {action}"))

    # 7. Composite summary
    lines.append("")
    lines.append(f"COMPOSITE SCORE: {composite}/100")
    if composite >= 80:
        lines.append("This places the asset in the top tier of framework scoring, indicating strong alignment across weighted dimensions.")
    elif composite >= 65:
        lines.append("This score reflects solid fundamentals with room for improvement in specific dimensions.")
    else:
        lines.append("This score indicates the asset is being monitored but hasn't yet reached high-conviction thresholds.")

    return "\n".join(lines)


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
    parser = argparse.ArgumentParser(description="Run daily scoring pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Don't write output files")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Starting daily scoring pipeline (v2 - tiered weights)")
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
        logger.info(f"GLI status: {'contracting' if gli_downtrend else 'expanding'} (source: {gli_data['source']})")
    else:
        logger.info("GLI data unavailable - macro filter disabled")

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
        "framework_version": "2.0",
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
            "current": gli_data["current"],
            "offset_value": gli_data["offset_value"],
            "offset_days": gli_data["offset_days"],
            "source": gli_data["source"],
        },
        "rs": {
            "enabled": config.rs.enabled,
            "lookback_days": config.rs.lookback_days,
            "threshold_pct": config.rs.underperformance_threshold * 100,
        },
        "assets": [],
    }

    # Process all assets (tiers computed dynamically from composite scores)
    logger.info(f"\nProcessing {len(assets_list)} assets...")
    for entry in assets_list:
        try:
            asset = build_asset(entry, conn, gli_downtrend=gli_downtrend)

            # Save to database
            migrations.save_snapshot(conn, asset, today)

            output["assets"].append(asset)
            logger.info(f"  {asset['symbol']} ({asset['tier']}): composite={asset['composite']}, action={asset['action']}")

        except Exception as e:
            logger.error(f"  Failed to process {entry.get('symbol', 'unknown')}: {e}")
            continue

    # Sort assets by tier priority then composite score
    tier_order = {"leader": 0, "runner-up": 1, "observation": 2}
    output["assets"].sort(key=lambda a: (tier_order.get(a["tier"], 3), -a["composite"]))

    # Commit database changes
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
