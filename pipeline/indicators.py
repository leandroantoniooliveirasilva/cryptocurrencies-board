#!/usr/bin/env python3
"""
Daily indicators update - RSI, GLI, RS vs BTC, Fear & Greed.

This lightweight script runs daily to update technical indicators without
re-running the full scoring pipeline. Full scoring (qualitative dimensions,
Wyckoff) runs weekly via run.py.

Usage:
    python -m pipeline.indicators
    python -m pipeline.indicators --dry-run
"""

from dotenv import load_dotenv
load_dotenv()

import argparse
import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

from pipeline.config import config
from pipeline.fetchers import defillama, fear_greed, gli, relative_strength
from pipeline.scoring import actions, rsi
from pipeline.storage import migrations

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
DB_PATH = REPO_ROOT / "pipeline" / "storage" / "history.sqlite"
PUBLIC_DIR = REPO_ROOT / "public"
LATEST_JSON = PUBLIC_DIR / "latest.json"


def _aggregate_weekly_prices(
    dated_prices: list[tuple[date, float]]
) -> list[float]:
    """Aggregate dated daily prices into weekly closes."""
    if not dated_prices or len(dated_prices) < 7:
        return []

    weeks: dict[tuple[int, int], tuple[date, float]] = {}
    for price_date, price in dated_prices:
        iso_year, iso_week, _ = price_date.isocalendar()
        week_key = (iso_year, iso_week)
        existing = weeks.get(week_key)
        if existing is None or price_date >= existing[0]:
            weeks[week_key] = (price_date, price)

    sorted_weeks = sorted(weeks.keys())
    return [weeks[week][1] for week in sorted_weeks]


def load_latest() -> dict:
    """Load existing latest.json."""
    if not LATEST_JSON.exists():
        raise FileNotFoundError(f"No existing data found at {LATEST_JSON}. Run full pipeline first.")

    with open(LATEST_JSON) as f:
        return json.load(f)


def update_asset_indicators(
    asset: dict,
    conn,
    gli_downtrend: bool,
    fg_greedy: bool,
) -> dict:
    """
    Update indicators for a single asset without re-scoring dimensions.

    Updates: RSI (daily/weekly), RS vs BTC, action state.
    Preserves: All qualitative scores, Wyckoff phase, composite.
    """
    symbol = asset["symbol"]
    coingecko_id = asset.get("coingecko_id")

    # Fetch fresh price data for RSI
    data_cfg = config.data
    dated_prices = (
        defillama.fetch_daily_prices_with_timestamps(
            coingecko_id, days=data_cfg.price_history_days
        )
        if coingecko_id
        else None
    )

    dated_daily: list[tuple[date, float]] = []
    if dated_prices:
        for ts, price in dated_prices:
            price_date = datetime.fromtimestamp(ts, tz=timezone.utc).date()
            dated_daily.append((price_date, price))
    daily_prices = [price for _d, price in dated_daily]
    weekly_prices = _aggregate_weekly_prices(dated_daily)

    # Compute RSI
    rsi_period = config.rsi.period
    rsi_daily = rsi.compute_rsi(daily_prices, rsi_period) if len(daily_prices) >= data_cfg.min_daily_points else None
    rsi_weekly = rsi.compute_rsi(weekly_prices, rsi_period) if len(weekly_prices) >= data_cfg.min_weekly_points else None

    # Weekly RSI from 4 weeks ago for slope check
    rsi_weekly_4w_ago = None
    if len(weekly_prices) >= data_cfg.min_weekly_points + 4:
        weekly_prices_4w_ago = weekly_prices[:-4]
        rsi_weekly_4w_ago = rsi.compute_rsi(weekly_prices_4w_ago, rsi_period)

    # Relative Strength vs BTC
    rs_data = relative_strength.compute_relative_strength(dated_prices, symbol)
    rs_underperforming = rs_data["underperforming"]

    # Get trend data for action derivation
    trend_7d = migrations.get_trend_data(conn, symbol, 7)
    trend_30d = migrations.get_trend_data(conn, symbol, 30)
    composite_last_week = migrations.get_composite_last_week(conn, symbol)

    composite_score = asset["composite"]
    if trend_7d:
        trend_7d.append(composite_score)
    else:
        trend_7d = [composite_score]
    if trend_30d:
        trend_30d.append(composite_score)
    else:
        trend_30d = [composite_score]

    effective_last_week = composite_last_week if composite_last_week is not None else composite_score

    # Re-derive action with updated indicators
    action = actions.derive_action(
        composite=composite_score,
        composite_last_week=effective_last_week,
        tier=asset["tier"],
        wyckoff_phase=asset["wyckoff_phase"],
        trend_7d=trend_7d,
        trend_30d=trend_30d,
        rsi_daily=rsi_daily,
        rsi_weekly=rsi_weekly,
        rsi_weekly_4w_ago=rsi_weekly_4w_ago,
        gli_downtrend=gli_downtrend,
        rs_underperforming=rs_underperforming,
        fg_greedy=fg_greedy,
    )

    # Update asset with fresh indicator data
    asset["rsi_daily"] = rsi_daily
    asset["rsi_weekly"] = rsi_weekly
    asset["action"] = action
    asset["rs_vs_btc"] = {
        "underperforming": rs_data["underperforming"],
        "change_pct": rs_data["rs_change_pct"],
    }
    asset["trend"] = trend_7d[-7:]
    asset["trend_30d"] = trend_30d[-30:]

    return asset


def main():
    parser = argparse.ArgumentParser(description="Update daily indicators (RSI, GLI, RS, F&G)")
    parser.add_argument("--dry-run", action="store_true", help="Don't write output files")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Daily indicators update")
    logger.info("=" * 60)

    # Load existing data
    try:
        data = load_latest()
    except FileNotFoundError as e:
        logger.error(str(e))
        return 1

    logger.info(f"Loaded {len(data['assets'])} assets from latest.json")

    # Fetch macro filters
    gli_data = gli.fetch_gli_data()
    gli_downtrend = gli_data["downtrend"]
    if gli_data["source"] != "fallback":
        logger.info(f"GLI status: {'contracting' if gli_downtrend else 'expanding'} (source: {gli_data['source']})")
    else:
        logger.info("GLI data unavailable - macro filter disabled")

    fg_data = fear_greed.fetch_fear_greed()
    fg_greedy = fg_data.get("greedy", False)
    if fg_data.get("enabled") and fg_data.get("value") is not None:
        logger.info(f"Fear & Greed: {fg_data['value']} ({fg_data['classification']}) - {'GREEDY' if fg_greedy else 'neutral'}")
    else:
        logger.info("Fear & Greed data unavailable - sentiment filter disabled")

    # Clear RS cache
    relative_strength.clear_cache()

    # Initialize database (read-only for trends)
    conn = migrations.init_db(DB_PATH)

    # Update GLI and F&G in output
    data["gli"] = {
        "enabled": config.gli.enabled,
        "downtrend": gli_downtrend,
        "current": gli_data["current"],
        "offset_value": gli_data["offset_value"],
        "offset_days": gli_data["offset_days"],
        "source": gli_data["source"],
    }
    data["fear_greed"] = {
        "enabled": fg_data.get("enabled", False),
        "value": fg_data.get("value"),
        "classification": fg_data.get("classification"),
        "threshold": fg_data.get("threshold", 70),
        "greedy": fg_greedy,
    }

    # We need coingecko_id for price fetching, load from assets.yaml
    import yaml
    assets_file = REPO_ROOT / "pipeline" / "assets.yaml"
    with open(assets_file) as f:
        assets_config = yaml.safe_load(f)
    assets_list = assets_config.get("assets", [])

    # Build lookup for coingecko_id
    coingecko_lookup = {a["symbol"]: a.get("coingecko_id") for a in assets_list}

    # Update each asset's indicators
    logger.info(f"\nUpdating indicators for {len(data['assets'])} assets...")
    for asset in data["assets"]:
        symbol = asset["symbol"]
        asset["coingecko_id"] = coingecko_lookup.get(symbol)

        try:
            update_asset_indicators(asset, conn, gli_downtrend, fg_greedy)
            # Remove temporary coingecko_id from output
            del asset["coingecko_id"]
            rsi_d_str = f"{asset['rsi_daily']:.1f}" if asset['rsi_daily'] else 'N/A'
            logger.info(f"  {symbol}: rsi_d={rsi_d_str}, action={asset['action']}")
        except Exception as e:
            logger.error(f"  Failed to update {symbol}: {e}")
            if "coingecko_id" in asset:
                del asset["coingecko_id"]

    conn.close()

    # Update timestamp
    data["generated_at"] = datetime.now(timezone.utc).isoformat()

    # Write output
    if args.dry_run:
        logger.info("DRY RUN - would update latest.json")
        logger.info(f"GLI downtrend: {gli_downtrend}, F&G greedy: {fg_greedy}")
        return 0

    with open(LATEST_JSON, "w") as f:
        json.dump(data, f, indent=2)
    logger.info(f"\nWrote {LATEST_JSON}")

    logger.info("\n" + "=" * 60)
    logger.info("Daily indicators update complete")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
