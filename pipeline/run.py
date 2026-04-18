#!/usr/bin/env python3
"""
Pipeline orchestrator - daily scoring scan.

Usage:
    python -m pipeline.run
    python -m pipeline.run --dry-run
"""

import argparse
import json
import logging
import sys
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

import yaml

from pipeline.config import config
from pipeline.fetchers import defillama, qualitative, supply
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


def _aggregate_weekly_prices(daily_prices: list) -> list:
    """
    Aggregate daily prices into weekly prices by taking the last price of each ISO week.

    This handles missing days and data gaps correctly, unlike simple slicing.
    Assumes daily_prices is ordered oldest to newest, representing the last N days.

    Args:
        daily_prices: List of daily closing prices (oldest to newest)

    Returns:
        List of weekly closing prices (last price of each ISO week)
    """
    if not daily_prices or len(daily_prices) < 7:
        return []

    # Calculate the date for each price (assuming prices end at today)
    today = date.today()
    prices_with_dates = []
    for i, price in enumerate(daily_prices):
        # Index 0 is the oldest, so days_ago = len - 1 - i
        days_ago = len(daily_prices) - 1 - i
        price_date = today - timedelta(days=days_ago)
        prices_with_dates.append((price_date, price))

    # Group by ISO week (year, week_number)
    weeks = {}
    for price_date, price in prices_with_dates:
        iso_year, iso_week, _ = price_date.isocalendar()
        week_key = (iso_year, iso_week)
        # Keep only the last (most recent) price for each week
        weeks[week_key] = price

    # Sort by week and return prices
    sorted_weeks = sorted(weeks.keys())
    return [weeks[week] for week in sorted_weeks]


def load_config() -> dict:
    """Load asset configuration from YAML."""
    try:
        with open(ASSETS_FILE) as f:
            config = yaml.safe_load(f)
            if not config or not isinstance(config, dict):
                logger.error(f"Invalid config in {ASSETS_FILE}: expected dict")
                return {"leaders": [], "runner_ups": [], "observation": []}
            return config
    except FileNotFoundError:
        logger.error(f"Assets file not found: {ASSETS_FILE}")
        return {"leaders": [], "runner_ups": [], "observation": []}
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse {ASSETS_FILE}: {e}")
        return {"leaders": [], "runner_ups": [], "observation": []}


def build_asset(entry: dict, tier: str, conn) -> dict:
    """
    Build complete asset data from config entry.

    Args:
        entry: Asset config from YAML
        tier: Asset tier (leader, runner-up, observation)
        conn: Database connection

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
    daily_prices = defillama.fetch_daily_prices(coingecko_id, days=data_cfg.price_history_days) if coingecko_id else None
    daily_prices = daily_prices or []  # Handle None from API failures

    # For weekly RSI, group by ISO week and take last price of each week
    # This handles missing days and data gaps correctly
    weekly_prices = _aggregate_weekly_prices(daily_prices)

    rsi_period = config.rsi.period
    rsi_daily = rsi.compute_rsi(daily_prices, rsi_period) if len(daily_prices) >= data_cfg.min_daily_points else None
    rsi_weekly = rsi.compute_rsi(weekly_prices, rsi_period) if len(weekly_prices) >= data_cfg.min_weekly_points else None

    # Detect Wyckoff phase from price structure (or use manual override)
    if wyckoff_override:
        wyckoff_phase = wyckoff_override
        wyckoff_score = wyckoff.get_wyckoff_score(wyckoff_phase)
    elif len(daily_prices) >= data_cfg.min_wyckoff_days:
        wyckoff_phase, wyckoff_score = wyckoff.detect_wyckoff_phase(daily_prices)
    else:
        wyckoff_phase = "Unknown"
        wyckoff_score = 50

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

    # Compute revenue score
    revenue_score = 50  # Default neutral
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

    # Derive action
    action = actions.derive_action(
        composite=composite_score,
        composite_last_week=composite_last_week or composite_score,
        tier=tier,
        wyckoff_phase=wyckoff_phase,
        trend_7d=trend_7d,
        trend_30d=trend_30d,
        rsi_daily=rsi_daily,
        rsi_weekly=rsi_weekly,
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
    )

    return {
        "symbol": symbol,
        "name": name,
        "tier": tier,
        "asset_type": asset_type,
        "scores": scores,
        "weights": weights,
        "composite": composite_score,
        "composite_last_week": composite_last_week or composite_score,
        "wyckoff_phase": wyckoff_phase,
        "trend": trend_7d[-7:],  # Last 7 days
        "trend_30d": trend_30d[-30:],  # Last 30 days
        "rsi_daily": rsi_daily,
        "rsi_weekly": rsi_weekly,
        "action": action,
        "strong_accumulate_days_active": strong_accumulate_days + (1 if action == "strong-accumulate" else 0),
        "label_changed_days_ago": label_changed_days_ago,
        "missing_dimensions": missing_dimensions,
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
    if "c" in wyckoff_phase.lower():
        notes.append("Wyckoff spring zone")
    elif "distribution" in wyckoff_phase.lower():
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
    rev_score = scores.get("revenue", 0)
    rev_weight = weights.get("revenue", 0)
    if rev_score >= 80:
        rev_desc = "Strong fee generation indicating sustainable protocol economics."
    elif rev_score >= 50:
        rev_desc = "Moderate revenue, typical for growth-phase protocols."
    else:
        rev_desc = "Limited fee revenue—protocol may rely on token incentives or is early-stage."
    lines.append(f"• Revenue/Fees ({rev_score}/100, {int(rev_weight*100)}% weight): {rev_desc}")

    # Wyckoff
    wyck_score = scores.get("wyckoff", 50)
    wyck_weight = weights.get("wyckoff", 0)
    phase_lower = wyckoff_phase.lower()
    if "accumulation" in phase_lower or "phase c" in phase_lower:
        wyck_desc = f"Currently in {wyckoff_phase}—historically favorable for position building as price structure suggests markup potential."
    elif "distribution" in phase_lower:
        wyck_desc = f"Currently in {wyckoff_phase}—caution warranted as price structure suggests potential markdown phase ahead."
    elif "markup" in phase_lower:
        wyck_desc = f"Currently in {wyckoff_phase}—trend is favorable but entries should be measured as some move has already occurred."
    else:
        wyck_desc = f"Currently in {wyckoff_phase}. Technical structure is being monitored for clearer phase identification."
    lines.append(f"• Wyckoff ({wyck_score}/100, {int(wyck_weight*100)}% weight): {wyck_desc}")

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

    # 5. Action reasoning
    lines.append("")
    lines.append("CURRENT ACTION:")
    action_reasoning = {
        "strong-accumulate": f"STRONG ACCUMULATE is firing because daily RSI shows a short-term oversold flush while weekly RSI and composite score remain healthy. This dislocation within an otherwise solid structure represents a high-conviction entry window.",
        "accumulate": f"ACCUMULATE status indicates this Leader-tier asset meets tranche-building criteria: composite above threshold, favorable Wyckoff phase, and RSI not overbought. Systematic position building is appropriate.",
        "promote": f"PROMOTE CANDIDATE status signals this Runner-up is demonstrating Leader-quality metrics. Manual review recommended for potential tier promotion.",
        "hold": f"HOLD status indicates the position is active with no current add or trim signals. Current allocation is appropriate—patience is the strategy.",
        "await": f"AWAIT status means signals are building but not yet confirmed. The asset shows promise but hasn't crossed activation thresholds.",
        "observe": f"OBSERVE status reflects Observation-tier placement—tracked for research, not positioned. No action required.",
        "stand-aside": f"STAND ASIDE is active due to distribution risk or sharp negative trend. Capital preservation takes priority regardless of price action.",
    }
    lines.append(action_reasoning.get(action, f"Current action: {action}"))

    # 6. Composite summary
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
    history_path = PUBLIC_DIR / "history.json"

    if dry_run:
        logger.info("DRY RUN - would write to:")
        logger.info(f"  {latest_path}")
        logger.info(f"  {history_path}")
        logger.info(f"Output preview:\n{json.dumps(output, indent=2)[:2000]}...")
        return

    with open(latest_path, "w") as f:
        json.dump(output, f, indent=2)
    logger.info(f"Wrote {latest_path}")

    # History file would be populated from DB
    # For now, just maintain compatibility
    with open(history_path, "w") as f:
        json.dump({"snapshots": []}, f, indent=2)
    logger.info(f"Wrote {history_path}")


def main():
    parser = argparse.ArgumentParser(description="Run daily scoring pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Don't write output files")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Starting daily scoring pipeline (v2 - tiered weights)")
    logger.info("=" * 60)

    # Load config
    config = load_config()
    total_assets = sum(len(v) for k, v in config.items() if isinstance(v, list))
    logger.info(f"Loaded {total_assets} assets from config")

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
        "assets": [],
    }

    # Process all tiers
    tier_map = [
        ("leader", config.get("leaders", [])),
        ("runner-up", config.get("runner_ups", [])),
        ("observation", config.get("observation", [])),
    ]

    for tier, entries in tier_map:
        logger.info(f"\nProcessing {tier} tier ({len(entries)} assets)...")
        for entry in entries:
            try:
                asset = build_asset(entry, tier, conn)

                # Save to database
                migrations.save_snapshot(conn, asset, today)

                output["assets"].append(asset)
                logger.info(f"  {asset['symbol']} ({asset['asset_type']}): composite={asset['composite']}, action={asset['action']}")

            except Exception as e:
                logger.error(f"  Failed to process {entry.get('symbol', 'unknown')}: {e}")
                continue

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
