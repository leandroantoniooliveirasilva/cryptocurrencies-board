"""Automated Wyckoff phase detection using price structure analysis.

Wyckoff Accumulation Phases:
- Phase A: Selling climax, price finds support after sharp decline
- Phase B: Building cause, sideways consolidation, testing bounds
- Phase C: Spring/test, final shakeout below support
- Phase D: Sign of strength, higher lows forming
- Phase E: Markup, breakout and trend begins

Wyckoff Distribution Phases:
- Phase A: Preliminary supply, buying climax near highs
- Phase B: Building cause, sideways near highs
- Phase C: UTAD, false breakout above resistance
- Phase D: Sign of weakness, lower highs forming
- Phase E: Markdown, breakdown and downtrend

This module uses heuristics based on:
1. Price position relative to 52-week range
2. Recent trend direction and magnitude
3. Volatility patterns
4. Support/resistance tests
"""

from typing import Optional, Tuple
import statistics


def detect_wyckoff_phase(
    daily_prices: list[float],
    lookback_days: int = 90
) -> Tuple[str, int]:
    """
    Detect current Wyckoff phase from price data.

    Args:
        daily_prices: List of daily closing prices (oldest to newest)
        lookback_days: Days to analyze (default 90)

    Returns:
        Tuple of (phase_string, score 0-100)
        Higher score = more bullish positioning
    """
    if not daily_prices or len(daily_prices) < 30:
        return "Unknown", 50

    # Use last N days
    prices = daily_prices[-lookback_days:] if len(daily_prices) >= lookback_days else daily_prices

    current = prices[-1]
    high_90d = max(prices)
    low_90d = min(prices)
    range_90d = high_90d - low_90d if high_90d != low_90d else 1

    # Position in range (0 = at low, 1 = at high)
    position_in_range = (current - low_90d) / range_90d

    # Calculate trends
    trend_7d = _calculate_trend(prices, 7)
    trend_30d = _calculate_trend(prices, 30)

    # Volatility (recent vs historical)
    recent_vol = _calculate_volatility(prices[-14:]) if len(prices) >= 14 else 0
    historical_vol = _calculate_volatility(prices[-60:-14]) if len(prices) >= 60 else recent_vol

    vol_ratio = recent_vol / historical_vol if historical_vol > 0 else 1

    # Distance from highs/lows
    pct_from_high = (high_90d - current) / high_90d * 100 if high_90d > 0 else 0
    pct_from_low = (current - low_90d) / low_90d * 100 if low_90d > 0 else 0

    # Determine phase using heuristics
    phase, score = _classify_phase(
        position_in_range=position_in_range,
        trend_7d=trend_7d,
        trend_30d=trend_30d,
        vol_ratio=vol_ratio,
        pct_from_high=pct_from_high,
        pct_from_low=pct_from_low
    )

    return phase, score


def _calculate_trend(prices: list[float], days: int) -> float:
    """Calculate percentage trend over N days."""
    if len(prices) < days:
        return 0
    start = prices[-days]
    end = prices[-1]
    if start == 0:
        return 0
    return ((end - start) / start) * 100


def _calculate_volatility(prices: list[float]) -> float:
    """Calculate standard deviation of returns."""
    if len(prices) < 2:
        return 0
    returns = [(prices[i] - prices[i-1]) / prices[i-1] * 100
               for i in range(1, len(prices)) if prices[i-1] != 0]
    if not returns:
        return 0
    return statistics.stdev(returns) if len(returns) > 1 else 0


def _classify_phase(
    position_in_range: float,
    trend_7d: float,
    trend_30d: float,
    vol_ratio: float,
    pct_from_high: float,
    pct_from_low: float
) -> Tuple[str, int]:
    """
    Classify Wyckoff phase based on metrics.

    Returns (phase_string, bullish_score 0-100)
    """

    # === DISTRIBUTION PHASES (bearish) ===

    # Phase E Distribution: Markdown - sharp decline from highs
    if pct_from_high > 30 and trend_30d < -15:
        return "Distribution Phase E", 20

    # Phase D Distribution: Sign of weakness - lower highs, declining
    if pct_from_high > 20 and trend_7d < -5 and trend_30d < -10:
        return "Distribution Phase D", 25

    # Phase C Distribution: UTAD - near highs but failing
    if position_in_range > 0.8 and trend_7d < -3 and vol_ratio > 1.3:
        return "Distribution Phase C", 30

    # Phase B Distribution: Building cause near highs, sideways
    if position_in_range > 0.75 and abs(trend_30d) < 8 and pct_from_high < 15:
        return "Distribution Phase B", 35

    # Phase A Distribution: Preliminary supply, buying climax
    if position_in_range > 0.85 and trend_30d > 15:
        return "Distribution Phase A", 40

    # === ACCUMULATION PHASES (bullish) ===

    # Phase E Accumulation: Markup - breakout, strong uptrend
    if trend_30d > 20 and trend_7d > 5 and position_in_range > 0.7:
        return "Accumulation Phase E", 90

    # Phase D Accumulation: Sign of strength - higher lows, grinding up
    if trend_30d > 10 and trend_7d > 0 and position_in_range > 0.5:
        return "Accumulation Phase D", 82

    # Phase C Accumulation: Spring - near lows, volatility spike, reversal starting
    if position_in_range < 0.35 and trend_7d > 3 and vol_ratio > 1.2:
        return "Accumulation Phase C", 75

    # Phase B→C: Transitioning from consolidation to spring
    if position_in_range < 0.4 and position_in_range > 0.2 and abs(trend_30d) < 10:
        if trend_7d > 0:
            return "Accumulation Phase B→C", 70
        else:
            return "Accumulation Phase B", 60

    # Phase B Accumulation: Building cause - sideways consolidation
    if abs(trend_30d) < 12 and vol_ratio < 1.1:
        if position_in_range < 0.5:
            return "Accumulation Phase B", 58
        else:
            return "Re-accumulation", 65

    # Phase A Accumulation: Selling climax - sharp decline finding support
    if pct_from_high > 25 and trend_7d > -2 and trend_30d < -5:
        return "Accumulation Phase A", 52

    # === NEUTRAL/TRANSITIONAL ===

    # Markup trend (bullish continuation)
    if trend_30d > 15 and position_in_range > 0.6:
        return "Markup", 78

    # Markdown trend (bearish continuation)
    if trend_30d < -15 and position_in_range < 0.4:
        return "Markdown", 28

    # Ranging/unclear
    if abs(trend_30d) < 8:
        if position_in_range > 0.5:
            return "Range (upper)", 55
        else:
            return "Range (lower)", 48

    # Default fallback
    if trend_30d > 0:
        return "Uptrend", 62
    else:
        return "Downtrend", 42


def get_wyckoff_score(phase: str) -> int:
    """
    Get a normalized Wyckoff score (0-100) from phase string.

    Used for backward compatibility with manual phase overrides.
    """
    phase_lower = phase.lower()

    # Re-accumulation (must check before "accumulation")
    if "re-accumulation" in phase_lower:
        return 65

    # Distribution phases (bearish)
    if "distribution" in phase_lower:
        if "phase e" in phase_lower or "markdown" in phase_lower:
            return 20
        elif "phase d" in phase_lower:
            return 25
        elif "phase c" in phase_lower:
            return 30
        elif "phase b" in phase_lower:
            return 35
        elif "phase a" in phase_lower:
            return 40
        return 30

    # Accumulation phases (bullish) - scores aligned with detect_wyckoff_phase
    if "accumulation" in phase_lower or "phase" in phase_lower:
        if "phase e" in phase_lower or "markup" in phase_lower:
            return 90
        elif "phase d" in phase_lower:
            return 82
        elif "b→c" in phase_lower or "b->c" in phase_lower:
            return 70
        elif "phase c" in phase_lower:
            return 75
        elif "phase b" in phase_lower:
            return 60
        elif "phase a" in phase_lower:
            return 52
        return 55

    # Other phases
    if "markup" in phase_lower:
        return 78
    if "markdown" in phase_lower:
        return 28
    if "range" in phase_lower:
        if "upper" in phase_lower:
            return 55
        elif "lower" in phase_lower:
            return 48
        return 50
    if "uptrend" in phase_lower:
        return 62
    if "downtrend" in phase_lower:
        return 42
    if "pre-market" in phase_lower:
        return 50

    return 50  # Default neutral
