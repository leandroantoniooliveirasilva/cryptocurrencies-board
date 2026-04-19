#!/usr/bin/env python3
"""
Backtest strong-accumulate signal logic against historical data.

This script validates whether the GLI filter correctly prevents
false strong-accumulate signals during bear market conditions.

Usage:
    python -m backtest.strong_accumulate_backtest

Requirements:
    - FRED_API_KEY environment variable for M2 data
    - Internet connection for CoinGecko price data
"""

import json
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import requests

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.scoring.rsi import compute_rsi


@dataclass
class DayData:
    """Single day of backtest data."""
    date: date
    price: float
    daily_rsi: Optional[float]
    weekly_rsi: Optional[float]
    m2_current: Optional[float]
    m2_offset: Optional[float]
    gli_downtrend: bool
    signal: str  # What signal would have fired
    price_30d_later: Optional[float]  # For outcome analysis
    return_30d: Optional[float]  # % return 30 days later


@dataclass
class SignalEvent:
    """A strong-accumulate signal event for analysis."""
    date: date
    price: float
    daily_rsi: float
    weekly_rsi: float
    gli_downtrend: bool
    signal_type: str  # "capitulation" or "wyckoff_dip"
    return_30d: Optional[float]
    return_60d: Optional[float]
    return_90d: Optional[float]
    regime: str  # "bull", "bear", "transition"


# Known market regimes for classification
MARKET_REGIMES = {
    # 2017-2018 cycle
    (date(2017, 1, 1), date(2017, 12, 17)): "bull",
    (date(2017, 12, 18), date(2018, 12, 15)): "bear",
    (date(2018, 12, 16), date(2019, 6, 26)): "recovery",

    # 2019-2020
    (date(2019, 6, 27), date(2020, 3, 12)): "consolidation",
    (date(2020, 3, 13), date(2020, 3, 23)): "covid_crash",
    (date(2020, 3, 24), date(2021, 4, 14)): "bull",

    # 2021-2022 cycle
    (date(2021, 4, 15), date(2021, 7, 20)): "correction",
    (date(2021, 7, 21), date(2021, 11, 10)): "bull",
    (date(2021, 11, 11), date(2022, 11, 21)): "bear",

    # 2022-2024 cycle
    (date(2022, 11, 22), date(2024, 3, 14)): "bull",
    (date(2024, 3, 15), date(2024, 8, 5)): "correction",
    (date(2024, 8, 6), date(2025, 1, 20)): "bull",
    (date(2025, 1, 21), date(2025, 12, 31)): "uncertain",
}


def get_regime(d: date) -> str:
    """Get market regime for a given date."""
    for (start, end), regime in MARKET_REGIMES.items():
        if start <= d <= end:
            return regime
    return "unknown"


def fetch_btc_prices(start_date: date, end_date: date) -> dict[date, float]:
    """Fetch BTC daily prices using multiple sources."""
    print(f"Fetching BTC prices from {start_date} to {end_date}...")

    # Check cache first
    cache_file = Path(__file__).parent / "cache" / "btc_prices.json"
    if cache_file.exists():
        print(f"  Loading from cache...")
        with open(cache_file) as f:
            cached = json.load(f)
            prices = {datetime.strptime(d_str, "%Y-%m-%d").date(): p
                     for d_str, p in cached.items()}
            # Check if cache covers our range
            cached_dates = set(prices.keys())
            if start_date in cached_dates or (min(cached_dates) <= start_date):
                print(f"  Got {len(prices)} daily prices from cache")
                return prices

    # Try CoinGecko with demo header
    prices = {}
    chunk_days = 90  # Smaller chunks

    headers = {
        "accept": "application/json",
        "x-cg-demo-api-key": "CG-demo"  # Demo key
    }

    current_start = start_date
    while current_start < end_date:
        current_end = min(current_start + timedelta(days=chunk_days), end_date)

        url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart/range"
        start_ts = int(datetime.combine(current_start, datetime.min.time()).timestamp())
        end_ts = int(datetime.combine(current_end, datetime.max.time()).timestamp())

        params = {
            "vs_currency": "usd",
            "from": start_ts,
            "to": end_ts,
        }

        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)

            if resp.status_code == 401 or resp.status_code == 429:
                print(f"  CoinGecko rate limited, falling back to Yahoo Finance...")
                return fetch_btc_prices_yahoo(start_date, end_date)

            resp.raise_for_status()
            data = resp.json()

            for ts, price in data.get("prices", []):
                d = datetime.fromtimestamp(ts / 1000).date()
                prices[d] = price

            print(f"  Chunk {current_start} to {current_end}: {len(data.get('prices', []))} prices")

        except Exception as e:
            print(f"  Error: {e}, falling back to Yahoo Finance...")
            return fetch_btc_prices_yahoo(start_date, end_date)

        current_start = current_end + timedelta(days=1)
        import time
        time.sleep(1.5)

    # Cache the data
    cache_dir = Path(__file__).parent / "cache"
    cache_dir.mkdir(exist_ok=True)
    with open(cache_dir / "btc_prices.json", "w") as f:
        json.dump({d.isoformat(): p for d, p in prices.items()}, f)

    print(f"  Got {len(prices)} total daily prices")
    return prices


def fetch_btc_prices_yahoo(start_date: date, end_date: date) -> dict[date, float]:
    """Fallback: Fetch BTC prices from Yahoo Finance via yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        print("  Installing yfinance...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance", "-q"])
        import yfinance as yf

    print(f"  Fetching from Yahoo Finance...")
    btc = yf.Ticker("BTC-USD")
    hist = btc.history(start=start_date, end=end_date + timedelta(days=1))

    prices = {}
    for idx, row in hist.iterrows():
        d = idx.date()
        prices[d] = row["Close"]

    # Cache the data
    cache_dir = Path(__file__).parent / "cache"
    cache_dir.mkdir(exist_ok=True)
    with open(cache_dir / "btc_prices.json", "w") as f:
        json.dump({d.isoformat(): p for d, p in prices.items()}, f)

    print(f"  Got {len(prices)} daily prices from Yahoo Finance")
    return prices


def fetch_fred_m2(start_date: date, end_date: date, api_key: str) -> dict[date, float]:
    """Fetch M2 money supply from FRED."""
    print(f"Fetching FRED M2 from {start_date} to {end_date}...")

    url = (
        f"https://api.stlouisfed.org/fred/series/observations"
        f"?series_id=M2SL"
        f"&api_key={api_key}"
        f"&file_type=json"
        f"&observation_start={start_date.isoformat()}"
        f"&observation_end={end_date.isoformat()}"
    )

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    m2_data = {}
    for obs in data.get("observations", []):
        if obs["value"] != ".":
            d = datetime.strptime(obs["date"], "%Y-%m-%d").date()
            m2_data[d] = float(obs["value"])

    print(f"  Got {len(m2_data)} M2 observations")
    return m2_data


def get_m2_for_date(d: date, m2_data: dict[date, float]) -> Optional[float]:
    """Get M2 value for a date (M2 is monthly, so find nearest prior)."""
    # M2 is released monthly, find the most recent value
    for days_back in range(60):
        check_date = d - timedelta(days=days_back)
        if check_date in m2_data:
            return m2_data[check_date]
    return None


def calculate_weekly_prices(daily_prices: dict[date, float]) -> dict[date, list[float]]:
    """
    Calculate weekly closing prices for RSI.
    Returns dict mapping each date to its trailing weekly closes.
    """
    sorted_dates = sorted(daily_prices.keys())
    weekly_closes = {}

    for i, d in enumerate(sorted_dates):
        # Get weekly closes (every 7th day going back)
        closes = []
        for j in range(i, -1, -7):
            if j >= 0:
                closes.append(daily_prices[sorted_dates[j]])
            if len(closes) >= 20:  # Enough for RSI calculation
                break
        weekly_closes[d] = list(reversed(closes))

    return weekly_closes


def simulate_signals(
    daily_prices: dict[date, float],
    m2_data: dict[date, float],
    offset_days: int = 75,
) -> list[SignalEvent]:
    """
    Simulate strong-accumulate signals using historical data.

    Returns list of all signal events with outcomes.
    """
    print("Simulating signals...")

    sorted_dates = sorted(daily_prices.keys())
    signals = []

    # Pre-calculate weekly prices
    weekly_closes = calculate_weekly_prices(daily_prices)

    # Need enough history for RSI
    min_history = 120  # days

    for i, d in enumerate(sorted_dates):
        if i < min_history:
            continue

        # Get trailing daily prices for RSI
        daily_trailing = [daily_prices[sorted_dates[j]] for j in range(i - min_history, i + 1)]

        # Calculate daily RSI
        daily_rsi = compute_rsi(daily_trailing, period=14)

        # Calculate weekly RSI
        weekly_trailing = weekly_closes.get(d, [])
        weekly_rsi = compute_rsi(weekly_trailing, period=14) if len(weekly_trailing) >= 15 else None

        if daily_rsi is None or weekly_rsi is None:
            continue

        # Get M2 values for GLI calculation
        m2_current = get_m2_for_date(d, m2_data)
        m2_offset_date = d - timedelta(days=offset_days)
        m2_offset = get_m2_for_date(m2_offset_date, m2_data)

        gli_downtrend = False
        if m2_current and m2_offset:
            gli_downtrend = m2_current < m2_offset

        # Check for signals
        signal_type = None

        # Path 1: Capitulation (both RSIs < 30)
        if weekly_rsi < 30 and daily_rsi < 30:
            signal_type = "capitulation"

        # Path 2: Wyckoff dip (daily flush, weekly intact)
        # Simplified: daily <= 32 and weekly >= 42
        elif daily_rsi <= 32 and weekly_rsi >= 42:
            signal_type = "wyckoff_dip"

        if signal_type:
            # Calculate forward returns
            price = daily_prices[d]

            return_30d = None
            return_60d = None
            return_90d = None

            if i + 30 < len(sorted_dates):
                price_30d = daily_prices[sorted_dates[i + 30]]
                return_30d = round((price_30d - price) / price * 100, 1)

            if i + 60 < len(sorted_dates):
                price_60d = daily_prices[sorted_dates[i + 60]]
                return_60d = round((price_60d - price) / price * 100, 1)

            if i + 90 < len(sorted_dates):
                price_90d = daily_prices[sorted_dates[i + 90]]
                return_90d = round((price_90d - price) / price * 100, 1)

            regime = get_regime(d)

            signals.append(SignalEvent(
                date=d,
                price=round(price, 2),
                daily_rsi=daily_rsi,
                weekly_rsi=weekly_rsi,
                gli_downtrend=gli_downtrend,
                signal_type=signal_type,
                return_30d=return_30d,
                return_60d=return_60d,
                return_90d=return_90d,
                regime=regime,
            ))

    print(f"  Found {len(signals)} signal events")
    return signals


def analyze_signals(signals: list[SignalEvent]) -> dict:
    """Analyze signal quality and GLI filter effectiveness."""

    results = {
        "total_signals": len(signals),
        "by_type": {},
        "by_regime": {},
        "gli_filter_analysis": {},
        "false_positives": [],
        "true_positives": [],
    }

    # Group by type
    for sig_type in ["capitulation", "wyckoff_dip"]:
        type_signals = [s for s in signals if s.signal_type == sig_type]

        if not type_signals:
            continue

        positive_30d = [s for s in type_signals if s.return_30d and s.return_30d > 0]
        positive_60d = [s for s in type_signals if s.return_60d and s.return_60d > 0]

        results["by_type"][sig_type] = {
            "count": len(type_signals),
            "hit_rate_30d": round(len(positive_30d) / len(type_signals) * 100, 1) if type_signals else 0,
            "hit_rate_60d": round(len(positive_60d) / len(type_signals) * 100, 1) if type_signals else 0,
            "avg_return_30d": round(np.mean([s.return_30d for s in type_signals if s.return_30d]), 1) if type_signals else 0,
            "gli_downtrend_count": len([s for s in type_signals if s.gli_downtrend]),
        }

    # Group by regime
    for regime in set(s.regime for s in signals):
        regime_signals = [s for s in signals if s.regime == regime]

        if not regime_signals:
            continue

        positive_30d = [s for s in regime_signals if s.return_30d and s.return_30d > 0]

        results["by_regime"][regime] = {
            "count": len(regime_signals),
            "hit_rate_30d": round(len(positive_30d) / len(regime_signals) * 100, 1),
            "avg_return_30d": round(np.mean([s.return_30d for s in regime_signals if s.return_30d]), 1),
            "gli_downtrend_count": len([s for s in regime_signals if s.gli_downtrend]),
        }

    # GLI filter effectiveness
    # Signals where GLI was NOT in downtrend
    gli_allowed = [s for s in signals if not s.gli_downtrend]
    gli_blocked = [s for s in signals if s.gli_downtrend]

    if gli_allowed:
        allowed_positive = [s for s in gli_allowed if s.return_30d and s.return_30d > 0]
        results["gli_filter_analysis"]["allowed"] = {
            "count": len(gli_allowed),
            "hit_rate_30d": round(len(allowed_positive) / len(gli_allowed) * 100, 1),
            "avg_return_30d": round(np.mean([s.return_30d for s in gli_allowed if s.return_30d]), 1),
        }

    if gli_blocked:
        blocked_positive = [s for s in gli_blocked if s.return_30d and s.return_30d > 0]
        blocked_negative = [s for s in gli_blocked if s.return_30d and s.return_30d < 0]
        results["gli_filter_analysis"]["blocked"] = {
            "count": len(gli_blocked),
            "would_have_been_positive": len(blocked_positive),
            "would_have_been_negative": len(blocked_negative),
            "correctly_blocked": len(blocked_negative),
            "incorrectly_blocked": len(blocked_positive),
        }

    # Identify false positives (bad signals that weren't blocked)
    for s in signals:
        if not s.gli_downtrend and s.return_30d and s.return_30d < -10:
            results["false_positives"].append({
                "date": s.date.isoformat(),
                "price": s.price,
                "type": s.signal_type,
                "regime": s.regime,
                "daily_rsi": s.daily_rsi,
                "weekly_rsi": s.weekly_rsi,
                "return_30d": s.return_30d,
            })

    # Identify true positives (good signals)
    for s in signals:
        if not s.gli_downtrend and s.return_30d and s.return_30d > 10:
            results["true_positives"].append({
                "date": s.date.isoformat(),
                "price": s.price,
                "type": s.signal_type,
                "regime": s.regime,
                "daily_rsi": s.daily_rsi,
                "weekly_rsi": s.weekly_rsi,
                "return_30d": s.return_30d,
            })

    return results


def print_report(signals: list[SignalEvent], analysis: dict):
    """Print a human-readable report."""

    print("\n" + "=" * 70)
    print("STRONG-ACCUMULATE BACKTEST REPORT")
    print("=" * 70)

    print(f"\nTotal signal events: {analysis['total_signals']}")

    print("\n--- BY SIGNAL TYPE ---")
    for sig_type, stats in analysis["by_type"].items():
        print(f"\n{sig_type.upper()}:")
        print(f"  Count: {stats['count']}")
        print(f"  Hit rate (30d): {stats['hit_rate_30d']}%")
        print(f"  Hit rate (60d): {stats['hit_rate_60d']}%")
        print(f"  Avg return (30d): {stats['avg_return_30d']}%")
        print(f"  GLI downtrend count: {stats['gli_downtrend_count']}")

    print("\n--- BY MARKET REGIME ---")
    for regime, stats in sorted(analysis["by_regime"].items()):
        print(f"\n{regime.upper()}:")
        print(f"  Count: {stats['count']}")
        print(f"  Hit rate (30d): {stats['hit_rate_30d']}%")
        print(f"  Avg return (30d): {stats['avg_return_30d']}%")
        print(f"  GLI downtrend: {stats['gli_downtrend_count']}")

    print("\n--- GLI FILTER EFFECTIVENESS ---")
    if "allowed" in analysis["gli_filter_analysis"]:
        allowed = analysis["gli_filter_analysis"]["allowed"]
        print(f"\nSignals ALLOWED (GLI expanding):")
        print(f"  Count: {allowed['count']}")
        print(f"  Hit rate (30d): {allowed['hit_rate_30d']}%")
        print(f"  Avg return (30d): {allowed['avg_return_30d']}%")

    if "blocked" in analysis["gli_filter_analysis"]:
        blocked = analysis["gli_filter_analysis"]["blocked"]
        print(f"\nSignals BLOCKED (GLI contracting):")
        print(f"  Count: {blocked['count']}")
        print(f"  Would have been positive: {blocked['would_have_been_positive']}")
        print(f"  Would have been negative: {blocked['would_have_been_negative']}")
        print(f"  Correctly blocked: {blocked['correctly_blocked']}")
        print(f"  Incorrectly blocked: {blocked['incorrectly_blocked']}")

    print("\n--- FALSE POSITIVES (unblocked signals with >10% loss) ---")
    if analysis["false_positives"]:
        for fp in analysis["false_positives"][:10]:
            print(f"  {fp['date']}: ${fp['price']:,.0f} | {fp['type']} | {fp['regime']} | "
                  f"RSI d:{fp['daily_rsi']} w:{fp['weekly_rsi']} | {fp['return_30d']}%")
    else:
        print("  None found! GLI filter caught all bad signals.")

    print("\n--- TOP TRUE POSITIVES (good signals) ---")
    sorted_tp = sorted(analysis["true_positives"], key=lambda x: x["return_30d"], reverse=True)
    for tp in sorted_tp[:10]:
        print(f"  {tp['date']}: ${tp['price']:,.0f} | {tp['type']} | {tp['regime']} | "
              f"RSI d:{tp['daily_rsi']} w:{tp['weekly_rsi']} | +{tp['return_30d']}%")

    print("\n" + "=" * 70)

    # Key insights
    print("\n🔑 KEY INSIGHTS:")

    fp_count = len(analysis["false_positives"])
    if fp_count == 0:
        print("  ✅ GLI filter caught ALL potentially bad signals")
    else:
        print(f"  ⚠️  {fp_count} false positives slipped through GLI filter")
        print("     Consider adding 'no recent capitulation' filter")

    # Check wyckoff_dip specifically in bear regimes
    bear_wyckoff = [s for s in signals
                   if s.signal_type == "wyckoff_dip"
                   and s.regime in ("bear", "correction")
                   and not s.gli_downtrend]
    if bear_wyckoff:
        print(f"\n  ⚠️  {len(bear_wyckoff)} wyckoff_dip signals in bear/correction NOT blocked by GLI:")
        for s in bear_wyckoff[:5]:
            print(f"      {s.date}: ${s.price:,.0f} | RSI d:{s.daily_rsi} w:{s.weekly_rsi} | {s.return_30d}%")


def save_results(signals: list[SignalEvent], analysis: dict, output_dir: Path):
    """Save results to JSON files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save all signals
    signals_data = [
        {
            "date": s.date.isoformat(),
            "price": s.price,
            "daily_rsi": s.daily_rsi,
            "weekly_rsi": s.weekly_rsi,
            "gli_downtrend": s.gli_downtrend,
            "signal_type": s.signal_type,
            "return_30d": s.return_30d,
            "return_60d": s.return_60d,
            "return_90d": s.return_90d,
            "regime": s.regime,
        }
        for s in signals
    ]

    with open(output_dir / "signals.json", "w") as f:
        json.dump(signals_data, f, indent=2)

    # Save analysis
    with open(output_dir / "analysis.json", "w") as f:
        json.dump(analysis, f, indent=2, default=str)

    print(f"\nResults saved to {output_dir}/")


def main():
    """Run the backtest."""

    # Check for FRED API key
    fred_key = os.environ.get("FRED_API_KEY")
    if not fred_key:
        print("ERROR: FRED_API_KEY environment variable required")
        print("Get a free key at: https://fred.stlouisfed.org/docs/api/api_key.html")
        sys.exit(1)

    # Date range for backtest
    end_date = date.today() - timedelta(days=1)
    start_date = date(2017, 1, 1)  # Start of 2017 bull run

    # Fetch data
    try:
        btc_prices = fetch_btc_prices(start_date, end_date)
        m2_data = fetch_fred_m2(start_date - timedelta(days=90), end_date, fred_key)
    except Exception as e:
        print(f"ERROR fetching data: {e}")
        sys.exit(1)

    # Run simulation
    signals = simulate_signals(btc_prices, m2_data, offset_days=75)

    # Analyze results
    analysis = analyze_signals(signals)

    # Print report
    print_report(signals, analysis)

    # Save results
    output_dir = Path(__file__).parent / "results"
    save_results(signals, analysis, output_dir)


if __name__ == "__main__":
    main()
