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
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from pipeline.fetchers import coingecko, defillama, qualitative, supply
from pipeline.scoring import actions, composite, rsi
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


def load_config() -> dict:
    """Load asset configuration from YAML."""
    with open(ASSETS_FILE) as f:
        return yaml.safe_load(f)


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

    # Fetch daily prices for RSI (market_chart endpoint gives true daily data)
    daily_prices = coingecko.fetch_daily_prices(coingecko_id, days=90) if coingecko_id else []

    # For weekly RSI, sample every 7th day from daily prices
    weekly_prices = daily_prices[::7] if len(daily_prices) >= 7 else []

    rsi_daily = rsi.compute_rsi(daily_prices, 14) if len(daily_prices) >= 15 else None
    rsi_weekly = rsi.compute_rsi(weekly_prices, 14) if len(weekly_prices) >= 15 else None

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

    # Compute supply/on-chain score
    exchange_trend = supply.get_exchange_reserve_trend(symbol)
    supply_score = supply.compute_supply_score(
        symbol=symbol,
        supply_metrics=None,  # Would fetch if not rate-limited
        exchange_reserve_trend=exchange_trend,
    )

    # Wyckoff score (placeholder - manual override or estimate)
    wyckoff_phase = wyckoff_override or "Phase A"
    wyckoff_score = _estimate_wyckoff_score(wyckoff_phase)

    # Build scores dict with all 5 dimensions
    scores = {
        "institutional": institutional_data["score"],
        "revenue": revenue_score,
        "regulatory": regulatory_data["score"],
        "supply": supply_score,
        "wyckoff": wyckoff_score,
    }

    # Compute composite with asset-type-specific weights
    composite_score = composite.compute_composite(scores, asset_type=asset_type)

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
        "note": note,
    }


def _estimate_wyckoff_score(phase: str) -> int:
    """Estimate Wyckoff dimension score from phase string."""
    phase_lower = phase.lower()

    if "distribution" in phase_lower:
        return 25
    elif "pre-accumulation" in phase_lower or "pre-market" in phase_lower:
        return 45
    elif "phase a" in phase_lower:
        return 55
    elif "phase b" in phase_lower:
        return 65
    elif "→c" in phase_lower or "b→c" in phase_lower:
        return 72
    elif "phase c" in phase_lower:
        return 78
    elif "phase d" in phase_lower or "phase e" in phase_lower:
        return 85
    else:
        return 50  # Unknown


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
