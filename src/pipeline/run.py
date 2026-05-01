#!/usr/bin/env python3
"""
Weekly full scoring pipeline — qualitative dimensions, composite, and tiers.

This runs the complete scoring pipeline including:
- Qualitative scores (regulatory, institutional) via CursorAgent CLI
- Revenue scores from DefiLlama
- Supply/on-chain analysis
- RSI calculation (daily/weekly)
- Macro filters (GLI, RS vs BTC, Fear & Greed)

Wyckoff phase is not a weighted dimension; it is refreshed on the daily
indicators job (``python -m pipeline.indicators``) and used only for action filters.

Scheduled via launchd: weekly dimension pass (Sunday 12:00 UTC, ``--dimensions-only``),
daily technicals via ``python -m pipeline.indicators`` (12:00 UTC).

Usage:
    python -m pipeline.run
    python -m pipeline.run --dimensions-only
    python -m pipeline.run --dry-run
"""

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

import argparse
import json
import logging
import os
import sqlite3
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from pipeline.repo_paths import pipeline_root, repo_root
from pipeline.category import (
    adoption_hint_for_category,
    resolve_asset_category,
    should_score_adoption_activity,
    should_score_value_capture,
    value_capture_skip_rationale,
)
from pipeline.config import config
from pipeline.fetchers import coingecko, defillama, fear_greed, gli, qualitative, relative_strength, supply
from pipeline.scoring import actions, composite, rsi
from pipeline.storage import migrations

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

REPO_ROOT = repo_root()
_PIPELINE_ROOT = pipeline_root()
ASSETS_FILE = _PIPELINE_ROOT / 'assets.yaml'
DB_PATH = _PIPELINE_ROOT / 'storage' / 'history.sqlite'
PUBLIC_DIR = REPO_ROOT / 'public'
LATEST_JSON = PUBLIC_DIR / 'latest.json'
# One JSON per asset per run; orchestrator merges assets into public/latest.json after all children finish.
SCORING_ASSET_OUTPUT_DIR = REPO_ROOT / 'out' / 'reports' / 'scoring' / 'assets'


def _score_asset_child_env() -> dict[str, str]:
    """
    Child processes run ``python -m pipeline.run``; they need ``src/`` on ``PYTHONPATH``
    when the venv has no editable install (scripts set this; IDEs may not).
    """
    env = dict(os.environ)
    src_root = str(REPO_ROOT / 'src')
    sep = os.pathsep
    parts = [p for p in env.get('PYTHONPATH', '').split(sep) if p]
    if src_root in parts:
        parts = [src_root] + [p for p in parts if p != src_root]
    else:
        parts = [src_root] + parts
    env['PYTHONPATH'] = sep.join(parts)
    return env


class DimensionScoringError(Exception):
    """Raised when a required weighted dimension is missing (strict scoring, no renormalisation)."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(', '.join(errors))


def _is_low_quality_rationale(rationale: Optional[str]) -> bool:
    text = (rationale or '').strip().lower()
    if not text:
        return True
    low_quality_markers = (
        'limited supply data available',
        'moderate usage signal; verify with on-chain data',
        'enterprise blockchain, pre-market',
    )
    return any(marker in text for marker in low_quality_markers)


def _collect_dimension_errors(
    scores: dict,
    asset_category: str,
    fee_model: Optional[str],
    weights_profile: dict[str, float],
) -> list[str]:
    """Return human-readable errors for any required weighted dimension that is missing."""
    errors: list[str] = []
    for dim, weight in weights_profile.items():
        if weight is None or float(weight) <= 0:
            continue
        if dim == 'value_capture' and not should_score_value_capture(weights_profile, fee_model):
            continue
        if dim == 'adoption_activity' and not should_score_adoption_activity(weights_profile):
            continue
        val = scores.get(dim)
        if val is None or (isinstance(val, float) and val != val):
            errors.append(f'{dim}:missing')
    return errors


def _load_macro_from_latest_json() -> tuple[dict, dict, dict]:
    """Reuse GLI / Fear&Greed / market_context from last published snapshot when running dimensions-only."""
    defaults_gli = {
        'enabled': config.gli.enabled,
        'downtrend': False,
        'trend': 'unknown',
        'current': None,
        'offset_value': None,
        'offset_days': config.gli.offset_days,
        'source': 'unchanged',
        'current_obs_date': None,
        'offset_obs_date': None,
        'component_coverage': None,
        'components_used': [],
        'components_missing': [],
    }
    defaults_fg = {
        'enabled': config.fear_greed.enabled,
        'value': None,
        'classification': None,
        'threshold': config.fear_greed.threshold,
        'greedy': False,
    }
    defaults_mc: dict = {'btc_dominance': None, 'stablecoin_mcap_billions': None, 'total_mcap_trillions': None}
    if not LATEST_JSON.exists():
        return defaults_gli, defaults_fg, defaults_mc
    try:
        with open(LATEST_JSON) as f:
            prev = json.load(f)
        gli = prev.get('gli') or defaults_gli
        fg = prev.get('fear_greed') or defaults_fg
        mc = prev.get('market_context') or defaults_mc
        return gli, fg, mc
    except (json.JSONDecodeError, OSError):
        return defaults_gli, defaults_fg, defaults_mc


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


def build_asset(
    entry: dict,
    conn,
    gli_downtrend: bool = False,
    fg_greedy: bool = False,
    *,
    dimensions_only: bool = False,
) -> dict:
    """
    Build complete asset data from config entry.
    Tier is computed dynamically from composite score.

    Args:
        entry: Asset config from YAML
        conn: Database connection
        gli_downtrend: True if Global Liquidity Index is contracting
        fg_greedy: True if Fear & Greed Index >= threshold (market greed)
        dimensions_only: Weekly dimension pass — no price/RSI/RS/action; action left null for the daily job.

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

    data_cfg = config.data
    if dimensions_only:
        dated_prices = None
        dated_daily: list[tuple[date, float]] = []
        daily_prices: list[float] = []
        weekly_prices: list[float] = []
        rsi_daily = None
        rsi_weekly = None
        rsi_weekly_4w_ago = None
    else:
        # Fetch daily prices for RSI from DefiLlama (free, no rate limits)
        dated_prices = (
            defillama.fetch_daily_prices_with_timestamps(
                coingecko_id, days=data_cfg.price_history_days
            )
            if coingecko_id
            else None
        )
        dated_daily = []
        if dated_prices:
            for ts, price in dated_prices:
                price_date = datetime.fromtimestamp(ts, tz=timezone.utc).date()
                dated_daily.append((price_date, price))
        daily_prices = [price for _d, price in dated_daily]
        weekly_prices = _aggregate_weekly_prices(dated_daily)

        rsi_period = config.rsi.period
        rsi_daily = rsi.compute_rsi(daily_prices, rsi_period) if len(daily_prices) >= data_cfg.min_daily_points else None
        rsi_weekly = rsi.compute_rsi(weekly_prices, rsi_period) if len(weekly_prices) >= data_cfg.min_weekly_points else None

        rsi_weekly_4w_ago = None
        if len(weekly_prices) >= data_cfg.min_weekly_points + 4:
            weekly_prices_4w_ago = weekly_prices[:-4]
            rsi_weekly_4w_ago = rsi.compute_rsi(weekly_prices_4w_ago, rsi_period)

    # Wyckoff: not part of composite weights; daily job updates phase from price structure.
    # Weekly run carries forward last persisted phase (or YAML override) so actions stay coherent.
    if wyckoff_override:
        wyckoff_phase = wyckoff_override
        wyckoff_rationale = f'Manual override: {wyckoff_override}'
    else:
        persisted = migrations.get_last_wyckoff_phase(conn, symbol)
        wyckoff_phase = persisted if persisted else 'Unknown'
        wyckoff_rationale = (
            'Wyckoff phase is updated on the daily indicators run (price structure).'
            if wyckoff_phase == 'Unknown'
            else 'Wyckoff phase carried from last snapshot until the next daily indicators refresh.'
        )

    cache_writes: list[tuple[str, str, int, str]] = []

    def record_cache_write(asset_symbol: str, score_type: str, score: int, rationale: str) -> None:
        cache_writes.append((asset_symbol, score_type, score, rationale))

    # Get qualitative scores (cached or fresh)
    cached_regulatory = migrations.get_cached_qualitative_score(conn, symbol, "regulatory")
    cached_institutional = migrations.get_cached_qualitative_score(conn, symbol, "institutional")

    if cached_regulatory and not _is_low_quality_rationale(cached_regulatory.get('rationale')):
        regulatory_data = cached_regulatory
    else:
        regulatory_data = qualitative.score_regulatory(symbol, name, use_cache=False)
        record_cache_write(symbol, "regulatory", regulatory_data["score"], regulatory_data["rationale"])

    if cached_institutional and not _is_low_quality_rationale(cached_institutional.get('rationale')):
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
        if cached_vc and not _is_low_quality_rationale(cached_vc.get('rationale')):
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
        if cached_ad and not _is_low_quality_rationale(cached_ad.get('rationale')):
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

    scores = {
        "institutional": institutional_data["score"],
        "adoption_activity": adoption_score,
        "value_capture": value_capture_score,
        "regulatory": regulatory_data["score"],
        "supply": supply_score,
    }

    dim_errors = _collect_dimension_errors(scores, asset_category, fee_model, weights_profile)
    if dim_errors:
        raise DimensionScoringError(dim_errors)

    composite_score, missing_dimensions = composite.compute_composite(
        scores, asset_category=asset_category, fee_model=fee_model
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

    effective_last_week = (
        composite_last_week if composite_last_week is not None else composite_score
    )

    if dimensions_only:
        rs_data = {
            'underperforming': False,
            'rs_change_pct': None,
            'current_rs': None,
            'lookback_rs': None,
        }
        action = None
        decision_trace = None
    else:
        rs_data = relative_strength.compute_relative_strength(dated_prices, symbol)
        rs_underperforming = rs_data["underperforming"]
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
        "wyckoff_position_score": None,
        "wyckoff_signal": None,
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


def _get_max_workers(default_workers: int = 10) -> int:
    raw_value = os.environ.get("PIPELINE_MAX_WORKERS")
    if not raw_value:
        return default_workers
    try:
        parsed = int(raw_value)
        return max(1, parsed)
    except ValueError:
        logger.warning(f"Invalid PIPELINE_MAX_WORKERS={raw_value!r}, using {default_workers}")
        return default_workers


def _build_asset_worker(
    entry: dict,
    gli_downtrend: bool,
    fg_greedy: bool,
    *,
    dimensions_only: bool = False,
) -> dict:
    symbol = entry.get('symbol', 'unknown')
    name = entry.get('name', '')
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA busy_timeout = 60000')
    try:
        asset = build_asset(
            entry,
            conn,
            gli_downtrend=gli_downtrend,
            fg_greedy=fg_greedy,
            dimensions_only=dimensions_only,
        )
        return {
            'symbol': symbol,
            'name': name,
            'asset': asset,
            'error': None,
            'dimension_errors': None,
        }
    except DimensionScoringError as e:
        return {
            'symbol': symbol,
            'name': name,
            'asset': None,
            'error': None,
            'dimension_errors': e.errors,
        }
    except Exception as e:
        return {
            'symbol': symbol,
            'name': name,
            'asset': None,
            'error': str(e),
            'dimension_errors': None,
        }
    finally:
        conn.close()


def _ensure_asset_reports_dir(snapshot_date: str) -> Path:
    out_dir = SCORING_ASSET_OUTPUT_DIR / snapshot_date
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _score_asset_job(
    entry: dict,
    gli_downtrend: bool,
    fg_greedy: bool,
    dimensions_only: bool,
    asset_reports_dir_str: str,
) -> dict:
    """
    Run one asset in an isolated subprocess, write out/reports/scoring/assets/<date>/<SYM>.json.
    Safe for concurrent calls from a thread pool (each asset writes a distinct file).
    Never raises: failures become ``result['error']`` so the thread pool can finish all assets.
    """
    symbol = entry.get('symbol', 'unknown')
    name = entry.get('name', '')
    try:
        result = _run_asset_subprocess(
            entry,
            gli_downtrend=gli_downtrend,
            fg_greedy=fg_greedy,
            dimensions_only=dimensions_only,
        )
        out_dir = Path(asset_reports_dir_str)
        (out_dir / f'{symbol}.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    except OSError as e:
        logger.error(f'  Failed to write per-asset report for {symbol}: {e}')
        result = {
            'symbol': symbol,
            'name': name,
            'asset': None,
            'error': f'per_asset_write_failed:{e}',
            'dimension_errors': None,
        }
    except Exception as e:
        logger.error(f'  Scoring job failed for {symbol}: {e}')
        result = {
            'symbol': symbol,
            'name': name,
            'asset': None,
            'error': f'job_failed:{e}',
            'dimension_errors': None,
        }
    return {'symbol': symbol, 'result': result}


def _run_single_asset_mode(input_path: Path, output_path: Path) -> int:
    try:
        payload = json.loads(input_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as e:
        output_path.write_text(
            json.dumps({'symbol': 'unknown', 'error': f'invalid_input:{e}'}, indent=2),
            encoding='utf-8',
        )
        return 1

    entry = payload.get('entry') or {}
    result = _build_asset_worker(
        entry=entry,
        gli_downtrend=bool(payload.get('gli_downtrend', False)),
        fg_greedy=bool(payload.get('fg_greedy', False)),
        dimensions_only=bool(payload.get('dimensions_only', False)),
    )
    output_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return 0 if not result.get('error') else 1


def _run_asset_subprocess(
    entry: dict,
    *,
    gli_downtrend: bool,
    fg_greedy: bool,
    dimensions_only: bool,
) -> dict:
    payload = {
        'entry': entry,
        'gli_downtrend': gli_downtrend,
        'fg_greedy': fg_greedy,
        'dimensions_only': dimensions_only,
    }
    with tempfile.TemporaryDirectory(prefix='asset-score-') as tmpdir:
        tmp_path = Path(tmpdir)
        input_path = tmp_path / 'input.json'
        output_path = tmp_path / 'output.json'
        input_path.write_text(json.dumps(payload), encoding='utf-8')

        cmd = [
            sys.executable,
            '-m',
            'pipeline.run',
            '--score-asset-input',
            str(input_path),
            '--score-asset-output',
            str(output_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, env=_score_asset_child_env())

        if not output_path.exists():
            return {
                'symbol': entry.get('symbol', 'unknown'),
                'name': entry.get('name', ''),
                'asset': None,
                'error': f'child_process_failed:{proc.returncode}:{proc.stderr.strip()}',
                'dimension_errors': None,
            }
        try:
            return json.loads(output_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as e:
            return {
                'symbol': entry.get('symbol', 'unknown'),
                'name': entry.get('name', ''),
                'asset': None,
                'error': f'child_output_invalid:{e}',
                'dimension_errors': None,
            }



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
    action: Optional[str],
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
    if action is None:
        lines.append(
            "Pending: daily indicators job applies RSI, Wyckoff, GLI, Fear & Greed, and RS vs BTC to derive action."
        )
    else:
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
    parser = argparse.ArgumentParser(description='Run weekly scoring pipeline')
    parser.add_argument('--dry-run', action='store_true', help="Don't write output files")
    parser.add_argument(
        '--dimensions-only',
        action='store_true',
        help='Weighted dimensions + composite/tier only; skip RSI/RS/action; reuse macro from last latest.json.',
    )
    parser.add_argument('--score-asset-input', type=str, default=None, help=argparse.SUPPRESS)
    parser.add_argument('--score-asset-output', type=str, default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.score_asset_input and args.score_asset_output:
        return _run_single_asset_mode(Path(args.score_asset_input), Path(args.score_asset_output))

    logger.info('=' * 60)
    if args.dimensions_only:
        logger.info('Weekly dimension scoring (strict dimensions, composite/tier)')
    else:
        logger.info('Weekly full scoring pipeline')
    logger.info('=' * 60)

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

    if args.dimensions_only:
        gli_data, fg_data, mc = _load_macro_from_latest_json()
        gli_downtrend = bool(gli_data.get('downtrend'))
        fg_greedy = bool(fg_data.get('greedy'))
        logger.info('Reused GLI / Fear & Greed / market_context from previous latest.json')
        stablecoin_mcap = None
        global_market = {
            'btc_dominance': mc.get('btc_dominance'),
            'total_mcap': (mc.get('total_mcap_trillions') or 0) * 1e12,
        }
    else:
        gli_data = gli.fetch_gli_data()
        gli_downtrend = gli_data['downtrend']
        if gli_data['source'] != 'fallback':
            gli_trend = gli.get_gli_trend_label(gli_data)
            logger.info(f"GLI status: {gli_trend} (source: {gli_data['source']})")
        else:
            logger.info('GLI data unavailable - macro filter disabled')

        fg_data = fear_greed.fetch_fear_greed()
        fg_greedy = fg_data.get('greedy', False)
        if fg_data.get('enabled') and fg_data.get('value') is not None:
            fg_class = fg_data.get('classification') or 'unknown'
            logger.info(
                f"Fear & Greed: {fg_data['value']} ({fg_class}) - "
                f"{'GREEDY' if fg_greedy else 'neutral'}"
            )
        else:
            logger.info('Fear & Greed data unavailable - sentiment filter disabled')

        global_market = coingecko.fetch_global_market_data()
        stablecoin_mcap = coingecko.fetch_stablecoin_mcap()
        if global_market.get('btc_dominance'):
            logger.info(f"BTC dominance: {global_market['btc_dominance']}%")
        if stablecoin_mcap:
            logger.info(f"Stablecoin market cap: ${stablecoin_mcap/1e9:.1f}B")

        relative_strength.clear_cache()
        if config.rs.enabled:
            logger.info(
                f"RS filter enabled: {config.rs.lookback_days}d lookback, "
                f'{config.rs.underperformance_threshold*100:.0f}% threshold'
            )

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
            "current": gli_data.get("current"),
            "offset_value": gli_data.get("offset_value"),
            "offset_days": gli_data.get("offset_days"),
            "source": gli_data.get("source"),
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
        "market_context": (
            mc
            if args.dimensions_only
            else {
                'btc_dominance': global_market.get('btc_dominance'),
                'stablecoin_mcap_billions': round(stablecoin_mcap / 1e9, 1) if stablecoin_mcap else None,
                'total_mcap_trillions': round(global_market.get('total_mcap', 0) / 1e12, 2)
                if global_market.get('total_mcap')
                else None,
            }
        ),
        'run_mode': 'dimensions_only' if args.dimensions_only else 'full',
        'assets': [],
        'scoring_errors': [],
    }

    # Process all assets (tiers computed dynamically from composite scores)
    logger.info(f"\nProcessing {len(assets_list)} assets...")
    worker_count = min(_get_max_workers(), max(1, len(assets_list)))
    logger.info(
        f'Isolated child-process scoring per asset (parallel pool: {worker_count} workers)',
    )
    asset_reports_dir = _ensure_asset_reports_dir(today)
    ads = str(asset_reports_dir)

    if worker_count == 1 or len(assets_list) <= 1:
        job_payloads = [
            _score_asset_job(
                entry,
                gli_downtrend,
                fg_greedy,
                args.dimensions_only,
                ads,
            )
            for entry in assets_list
        ]
    else:
        by_index: dict[int, dict] = {}
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(
                    _score_asset_job,
                    entry,
                    gli_downtrend,
                    fg_greedy,
                    args.dimensions_only,
                    ads,
                ): i
                for i, entry in enumerate(assets_list)
            }
            for fut in as_completed(futures):
                by_index[futures[fut]] = fut.result()
        job_payloads = [by_index[i] for i in range(len(assets_list))]

    processed_assets: list[dict] = []
    scoring_errors: list[dict] = []
    for payload in job_payloads:
        result = payload['result']
        if result.get('dimension_errors'):
            scoring_errors.append({
                'symbol': result['symbol'],
                'name': result.get('name', ''),
                'errors': result['dimension_errors'],
            })
            logger.error(
                f"  Dimension scoring failed for {result['symbol']}: {result['dimension_errors']}"
            )
            continue
        if result.get('error'):
            logger.error(f"  Failed to process {result['symbol']}: {result['error']}")
            continue
        processed_assets.append(result['asset'])

    # Persist cache writes and snapshots in the master process only.
    for asset in processed_assets:
        if not args.dry_run:
            for symbol, score_type, score, rationale in asset.get('cache_writes', []):
                migrations.save_qualitative_score(conn, symbol, score_type, score, rationale)
            migrations.save_snapshot(
                conn,
                asset,
                today,
                preserve_null_technicals=args.dimensions_only,
            )

        asset.pop('cache_writes', None)
        output['assets'].append(asset)
        logger.info(
            f"  {asset['symbol']} ({asset['tier']}): composite={asset['composite']}, action={asset['action']}"
        )

    output['scoring_errors'] = scoring_errors

    # Sort assets by tier priority then composite score
    tier_order = {'leader': 0, 'runner-up': 1, 'observation': 2}
    output['assets'].sort(key=lambda a: (tier_order.get(a['tier'], 3), -a['composite']))

    # Commit database changes only when writes are enabled.
    if not args.dry_run:
        conn.commit()
    conn.close()

    # Write output
    write_output(output, dry_run=args.dry_run)

    logger.info('\n' + '=' * 60)
    logger.info(f"Pipeline complete. Processed {len(output['assets'])} assets.")
    if scoring_errors:
        logger.info(f"Scoring errors (excluded from tiers): {len(scoring_errors)}")
    logger.info('=' * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
