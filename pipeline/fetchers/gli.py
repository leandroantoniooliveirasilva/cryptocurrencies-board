"""Global Liquidity Index (GLI) fetcher.

Preferred source is a configurable central-bank balance-sheet composite (FRED),
with manual override and M2 fallback options.
"""

import csv
import io
import logging
import os
import time
from datetime import date, datetime, timedelta, timezone
from typing import Optional, TypedDict

import requests

from pipeline.config import config

logger = logging.getLogger(__name__)


class GLIData(TypedDict):
    """GLI data structure."""

    current: Optional[float]
    offset_value: Optional[float]
    offset_days: int
    downtrend: bool
    source: str
    fetched_at: str
    current_obs_date: Optional[str]
    offset_obs_date: Optional[str]
    trend: str
    component_coverage: float
    components_used: list[str]
    components_missing: list[str]


# Cache to avoid repeated fetches (keyed by offset_days)
_gli_cache: dict[int, GLIData] = {}
_gli_cache_time: dict[int, float] = {}
CACHE_TTL_SECONDS = 3600

# In-memory cache for FRED series observations (per series_id)
_fred_series_cache: dict[str, list[tuple[date, float]]] = {}
_bis_csv_cache: dict[str, list[tuple[date, float]]] = {}


def get_gli_trend_label(data: GLIData, epsilon: float = 1e-6) -> str:
    """Return human-friendly GLI trend label."""
    current = data.get('current')
    offset_value = data.get('offset_value')

    if current is None or offset_value is None:
        return 'unknown'

    delta = current - offset_value
    if abs(delta) <= epsilon:
        return 'flat'
    if delta < 0:
        return 'contracting'
    return 'expanding'


def fetch_gli_data(offset_days: Optional[int] = None) -> GLIData:
    """Fetch GLI data and determine trend."""
    gli_cfg = config.gli
    if offset_days is None:
        offset_days = gli_cfg.offset_days

    cache_time = _gli_cache_time.get(offset_days)
    if cache_time and (time.time() - cache_time) < CACHE_TTL_SECONDS:
        cached = _gli_cache.get(offset_days)
        if cached:
            return cached

    data = _try_manual_override(offset_days)
    if data:
        return _cache(offset_days, data)

    if getattr(gli_cfg, 'use_fred_composite', False):
        data = _try_fred_composite(offset_days)
        if data:
            return _cache(offset_days, data)

    data = _try_tradingview(offset_days)
    if data:
        return _cache(offset_days, data)

    if getattr(gli_cfg, 'allow_fred_m2_fallback', True):
        data = _try_fred_m2(offset_days)
        if data:
            return _cache(offset_days, data)

    logger.warning('GLI data unavailable - filter disabled')
    data = GLIData(
        current=None,
        offset_value=None,
        offset_days=offset_days,
        downtrend=False,
        source='fallback',
        fetched_at=datetime.now(timezone.utc).isoformat(),
        current_obs_date=None,
        offset_obs_date=None,
        trend='unknown',
        component_coverage=0.0,
        components_used=[],
        components_missing=[],
    )
    return _cache(offset_days, data)


def _cache(offset_days: int, data: GLIData) -> GLIData:
    _gli_cache[offset_days] = data
    _gli_cache_time[offset_days] = time.time()
    return data


def _try_manual_override(offset_days: int) -> Optional[GLIData]:
    gli_current = os.environ.get('GLI_CURRENT')
    gli_offset = os.environ.get('GLI_OFFSET')

    if gli_current and gli_offset:
        try:
            current = float(gli_current)
            offset_val = float(gli_offset)
            data = GLIData(
                current=current,
                offset_value=offset_val,
                offset_days=offset_days,
                downtrend=current < offset_val,
                source='manual_override',
                fetched_at=datetime.now(timezone.utc).isoformat(),
                current_obs_date=None,
                offset_obs_date=None,
                trend='unknown',
                component_coverage=1.0,
                components_used=['manual_override'],
                components_missing=[],
            )
            data['trend'] = get_gli_trend_label(data)
            logger.info(f'GLI manual override: current={current}, offset={offset_val}')
            return data
        except ValueError:
            logger.warning('Invalid GLI manual override values')

    return None


def _fred_observations(api_key: str, series_id: str, start: date, end: date) -> list[tuple[date, float]]:
    cached = _fred_series_cache.get(series_id)
    if cached:
        return cached

    url = (
        'https://api.stlouisfed.org/fred/series/observations'
        f'?series_id={series_id}'
        f'&api_key={api_key}'
        '&file_type=json'
        f'&observation_start={start.isoformat()}'
        f'&observation_end={end.isoformat()}'
    )

    resp = requests.get(url, timeout=20)
    if resp.status_code != 200:
        return []

    raw = resp.json().get('observations', [])
    values: list[tuple[date, float]] = []
    for obs in raw:
        if obs.get('value') in (None, '.'):
            continue
        try:
            obs_date = datetime.strptime(obs['date'], '%Y-%m-%d').date()
            obs_value = float(obs['value'])
            values.append((obs_date, obs_value))
        except Exception:
            continue

    values.sort(key=lambda t: t[0])
    _fred_series_cache[series_id] = values
    return values


def _latest_on_or_before(values: list[tuple[date, float]], target: date) -> Optional[tuple[date, float]]:
    found: Optional[tuple[date, float]] = None
    for obs_date, obs_value in values:
        if obs_date <= target:
            found = (obs_date, obs_value)
        else:
            break
    return found


def _max_staleness_days(frequency: str) -> int:
    staleness_cfg = getattr(config.gli, 'staleness', None)
    if staleness_cfg is None:
        return 62
    if frequency == 'daily':
        return int(getattr(staleness_cfg, 'daily_max_days', 10))
    if frequency == 'weekly':
        return int(getattr(staleness_cfg, 'weekly_max_days', 21))
    return int(getattr(staleness_cfg, 'monthly_max_days', 62))


def _is_stale(obs_date: date, frequency: str, now_date: date) -> bool:
    return (now_date - obs_date).days > _max_staleness_days(frequency)


def _bis_observations_csv(url: str) -> list[tuple[date, float]]:
    cached = _bis_csv_cache.get(url)
    if cached is not None:
        return cached

    try:
        resp = requests.get(url, timeout=20)
        if resp.status_code != 200:
            _bis_csv_cache[url] = []
            return []

        reader = csv.DictReader(io.StringIO(resp.text))
        out: list[tuple[date, float]] = []
        for row in reader:
            raw_period = row.get('TIME_PERIOD')
            raw_value = row.get('OBS_VALUE')
            if not raw_period or not raw_value:
                continue
            try:
                if '-Q' in raw_period:
                    # Quarterly format: YYYY-Qx
                    year, quarter = raw_period.split('-Q')
                    month = {'1': 3, '2': 6, '3': 9, '4': 12}.get(quarter, 12)
                    obs_date = date(int(year), month, 1)
                else:
                    # Monthly format: YYYY-MM
                    parts = raw_period.split('-')
                    obs_date = date(int(parts[0]), int(parts[1]), 1)
                out.append((obs_date, float(raw_value)))
            except Exception:
                continue

        out.sort(key=lambda t: t[0])
        _bis_csv_cache[url] = out
        return out
    except Exception:
        _bis_csv_cache[url] = []
        return []


def _try_bis_pbc_series(
    current_target: date,
    offset_target: date,
    end_date: date,
) -> Optional[tuple[tuple[date, float], tuple[date, float]]]:
    bis_cfg = getattr(config.gli, 'bis', None)
    if bis_cfg is None:
        return None
    csv_url = getattr(bis_cfg, 'cbta_china_csv_url', None)
    if not csv_url:
        return None

    values = _bis_observations_csv(csv_url)
    if not values:
        return None

    current_obs = _latest_on_or_before(values, current_target)
    offset_obs = _latest_on_or_before(values, offset_target)
    if not current_obs or not offset_obs:
        return None

    if _is_stale(current_obs[0], 'monthly', end_date):
        return None

    # BIS series can be local currency or %GDP depending on the configured endpoint.
    # We include only if the values are in plausible local-currency scale (>1000).
    if current_obs[1] < 1000 or offset_obs[1] < 1000:
        return None

    return current_obs, offset_obs


def _try_fred_composite(offset_days: int) -> Optional[GLIData]:
    api_key = os.environ.get('FRED_API_KEY')
    if not api_key:
        return None

    end_date = date.today()
    start_date = end_date - timedelta(days=offset_days + 400)
    current_target = end_date
    offset_target = end_date - timedelta(days=offset_days)

    try:
        cfg = getattr(config.gli, 'components', None)
        if cfg is None:
            return None

        components = [
            ('fed', 'WALCL', 1.0, 'usd_million', +1.0, 'weekly'),
            ('tga', 'WTREGEN', 1.0, 'usd_million', -1.0, 'daily'),
            ('rrp', 'RRPONTSYD', 1000.0, 'usd_billion', -1.0, 'daily'),
            ('ecb', 'ECBASSETSW', 1.0, 'eur_million', +1.0, 'weekly'),
            ('boj', 'JPNASSETS', 100.0, 'jpy_100m', +1.0, 'monthly'),
        ]

        fx_eur = _fred_observations(api_key, 'DEXUSEU', start_date, end_date)
        fx_jpy = _fred_observations(api_key, 'DEXJPUS', start_date, end_date)

        current_sum = 0.0
        offset_sum = 0.0
        current_dates: list[date] = []
        offset_dates: list[date] = []
        enabled_count = 0
        used_components: list[str] = []
        missing_components: list[str] = []

        for key, series_id, base_multiplier, unit_kind, sign, frequency in components:
            if not bool(getattr(cfg, key, False)):
                continue
            enabled_count += 1

            obs = _fred_observations(api_key, series_id, start_date, end_date)
            current_obs = _latest_on_or_before(obs, current_target)
            offset_obs = _latest_on_or_before(obs, offset_target)

            if not current_obs or not offset_obs:
                missing_components.append(f'{key}:missing_series_data')
                continue
            if _is_stale(current_obs[0], frequency, end_date):
                missing_components.append(f'{key}:stale_current')
                continue

            current_value = current_obs[1] * base_multiplier
            offset_value = offset_obs[1] * base_multiplier

            if unit_kind == 'eur_million':
                fx_current = _latest_on_or_before(fx_eur, current_obs[0])
                fx_offset = _latest_on_or_before(fx_eur, offset_obs[0])
                if not fx_current or not fx_offset:
                    missing_components.append(f'{key}:missing_fx')
                    continue
                current_value = current_value * fx_current[1]
                offset_value = offset_value * fx_offset[1]
            elif unit_kind == 'jpy_100m':
                fx_current = _latest_on_or_before(fx_jpy, current_obs[0])
                fx_offset = _latest_on_or_before(fx_jpy, offset_obs[0])
                if not fx_current or not fx_offset or fx_current[1] == 0 or fx_offset[1] == 0:
                    missing_components.append(f'{key}:missing_fx')
                    continue
                current_value = current_value / fx_current[1]
                offset_value = offset_value / fx_offset[1]

            current_sum += sign * current_value
            offset_sum += sign * offset_value
            current_dates.append(current_obs[0])
            offset_dates.append(offset_obs[0])
            used_components.append(key)

        # Optional BIS PBC contribution (monthly, local-currency endpoint expected).
        if bool(getattr(cfg, 'pbc', False)):
            enabled_count += 1
            pbc_pair = _try_bis_pbc_series(current_target, offset_target, end_date)
            if not pbc_pair:
                missing_components.append('pbc:missing_or_invalid_bis')
            else:
                current_obs, offset_obs = pbc_pair

                # Convert CNY to USD using FRED daily CNYUSD quote (DEXCHUS: CNY per USD).
                fx_cny = _fred_observations(api_key, 'DEXCHUS', start_date, end_date)
                fx_current = _latest_on_or_before(fx_cny, current_obs[0])
                fx_offset = _latest_on_or_before(fx_cny, offset_obs[0])
                if not fx_current or not fx_offset or fx_current[1] == 0 or fx_offset[1] == 0:
                    missing_components.append('pbc:missing_fx')
                else:
                    # BIS/PBOC values expected in 100 million CNY.
                    current_usd_million = (current_obs[1] * 100.0) / fx_current[1]
                    offset_usd_million = (offset_obs[1] * 100.0) / fx_offset[1]
                    current_sum += current_usd_million
                    offset_sum += offset_usd_million
                    current_dates.append(current_obs[0])
                    offset_dates.append(offset_obs[0])
                    used_components.append('pbc')

        if bool(getattr(cfg, 'smaller_cb', False)):
            enabled_count += 1
            missing_components.append('smaller_cb:not_supported_series')

        if enabled_count == 0:
            return None

        coverage = len(used_components) / enabled_count
        min_coverage = float(getattr(config.gli, 'min_component_coverage', 0.6))
        if coverage < min_coverage:
            logger.warning(f'GLI composite coverage too low ({coverage:.2f} < {min_coverage:.2f})')
            return None

        # Inputs are in USD millions at this point; convert to trillions.
        current_trillion = current_sum / 1_000_000.0
        offset_trillion = offset_sum / 1_000_000.0

        data = GLIData(
            current=round(current_trillion, 3),
            offset_value=round(offset_trillion, 3),
            offset_days=offset_days,
            downtrend=current_trillion < offset_trillion,
            source='fred_composite',
            fetched_at=datetime.now(timezone.utc).isoformat(),
            current_obs_date=max(current_dates).isoformat() if current_dates else None,
            offset_obs_date=max(offset_dates).isoformat() if offset_dates else None,
            trend='unknown',
            component_coverage=round(coverage, 2),
            components_used=used_components,
            components_missing=missing_components,
        )
        data['trend'] = get_gli_trend_label(data)
        logger.info(
            f"GLI composite from FRED: current={data['current']}T, offset={data['offset_value']}T, "
            f"coverage={data['component_coverage']:.2f}, used={','.join(used_components)}, "
            f"obs={data['current_obs_date']}/{data['offset_obs_date']}"
        )
        return data

    except Exception as e:
        logger.debug(f'FRED composite GLI fetch failed: {e}')
        return None


def _try_tradingview(offset_days: int) -> Optional[GLIData]:
    if os.environ.get('GLI_TRY_TRADINGVIEW', '').lower() not in ('1', 'true', 'yes'):
        return None

    try:
        symbol = config.gli.tradingview_symbol
        url = 'https://scanner.tradingview.com/global/scan'
        payload = {
            'symbols': {'tickers': [symbol]},
            'columns': ['close', 'change'],
        }
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0',
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('data'):
                row = data['data'][0]
                if row.get('d'):
                    current = row['d'][0]
                    logger.info(f'GLI from TradingView: current={current}')

        return None

    except Exception as e:
        logger.debug(f'TradingView GLI fetch failed: {e}')
        return None


def _try_fred_m2(offset_days: int) -> Optional[GLIData]:
    api_key = os.environ.get('FRED_API_KEY')
    if not api_key:
        return None

    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=offset_days + 120)
        observations = _fred_observations(api_key, 'M2SL', start_date, end_date)
        if not observations:
            return None

        current_obs = _latest_on_or_before(observations, end_date)
        offset_obs = _latest_on_or_before(observations, end_date - timedelta(days=offset_days))
        if not current_obs or not offset_obs:
            return None

        data = GLIData(
            current=current_obs[1],
            offset_value=offset_obs[1],
            offset_days=offset_days,
            downtrend=current_obs[1] < offset_obs[1],
            source='fred_m2',
            fetched_at=datetime.now(timezone.utc).isoformat(),
            current_obs_date=current_obs[0].isoformat(),
            offset_obs_date=offset_obs[0].isoformat(),
            trend='unknown',
            component_coverage=1.0,
            components_used=['m2sl'],
            components_missing=[],
        )
        data['trend'] = get_gli_trend_label(data)
        logger.info(
            f"GLI (M2 proxy) from FRED: current={data['current']}, offset={data['offset_value']}, "
            f"obs={data['current_obs_date']}/{data['offset_obs_date']}"
        )
        return data

    except Exception as e:
        logger.debug(f'FRED M2 fetch failed: {e}')
        return None


def is_gli_downtrend() -> bool:
    if not config.gli.enabled:
        return False
    return fetch_gli_data()['downtrend']


def get_gli_status() -> dict:
    data = fetch_gli_data()

    if data['current'] is None:
        return {
            'available': False,
            'message': 'GLI data unavailable',
        }

    offset_value = data['offset_value']
    if offset_value is not None and offset_value != 0:
        pct_change = (data['current'] - offset_value) / offset_value * 100
    else:
        pct_change = 0

    trend = get_gli_trend_label(data)

    return {
        'available': True,
        'current': data['current'],
        'offset_value': data['offset_value'],
        'offset_days': data['offset_days'],
        'downtrend': data['downtrend'],
        'trend': trend,
        'pct_change': round(pct_change, 2),
        'message': f"GLI {trend} ({pct_change:+.1f}% vs {data['offset_days']}d ago)",
        'source': data['source'],
        'current_obs_date': data.get('current_obs_date'),
        'offset_obs_date': data.get('offset_obs_date'),
        'component_coverage': data.get('component_coverage', 0.0),
        'components_used': data.get('components_used', []),
        'components_missing': data.get('components_missing', []),
    }
