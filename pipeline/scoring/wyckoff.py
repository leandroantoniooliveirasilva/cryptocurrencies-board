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

All thresholds are configured in config.yaml.
"""

from typing import Optional, Tuple
import statistics

from pipeline.config import config


def detect_wyckoff_phase(
    daily_prices: list[float],
    lookback_days: Optional[int] = None
) -> Tuple[str, int]:
    """
    Detect current Wyckoff phase from price data.

    Args:
        daily_prices: List of daily closing prices (oldest to newest)
        lookback_days: Days to analyze (defaults to config.wyckoff.lookback_days)

    Returns:
        Tuple of (phase_string, score 0-100)
        Higher score = more bullish positioning
    """
    wyckoff_cfg = config.wyckoff
    scores_cfg = wyckoff_cfg.scores

    if lookback_days is None:
        lookback_days = wyckoff_cfg.lookback_days

    if not daily_prices or len(daily_prices) < 30:
        return "Unknown", scores_cfg.default

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

    All thresholds loaded from config.yaml.

    Returns (phase_string, bullish_score 0-100)
    """
    wyckoff_cfg = config.wyckoff
    dist_cfg = wyckoff_cfg.distribution
    acc_cfg = wyckoff_cfg.accumulation
    scores_cfg = wyckoff_cfg.scores

    # === DISTRIBUTION PHASES (bearish) ===

    # Phase E Distribution: Markdown - sharp decline from highs
    if pct_from_high > dist_cfg.phase_e.pct_from_high and trend_30d < dist_cfg.phase_e.trend_30d:
        return "Distribution Phase E", scores_cfg.distribution_phase_e

    # Phase D Distribution: Sign of weakness - lower highs, declining
    if (pct_from_high > dist_cfg.phase_d.pct_from_high and
        trend_7d < dist_cfg.phase_d.trend_7d and
        trend_30d < dist_cfg.phase_d.trend_30d):
        return "Distribution Phase D", scores_cfg.distribution_phase_d

    # Phase C Distribution: UTAD - near highs but failing
    if (position_in_range > dist_cfg.phase_c.position_in_range and
        trend_7d < dist_cfg.phase_c.trend_7d and
        vol_ratio > dist_cfg.phase_c.vol_ratio):
        return "Distribution Phase C", scores_cfg.distribution_phase_c

    # Phase B Distribution: Building cause near highs, sideways
    if (position_in_range > dist_cfg.phase_b.position_in_range and
        abs(trend_30d) < dist_cfg.phase_b.trend_30d_abs and
        pct_from_high < dist_cfg.phase_b.pct_from_high):
        return "Distribution Phase B", scores_cfg.distribution_phase_b

    # Phase A Distribution: Preliminary supply, buying climax
    if position_in_range > dist_cfg.phase_a.position_in_range and trend_30d > dist_cfg.phase_a.trend_30d:
        return "Distribution Phase A", scores_cfg.distribution_phase_a

    # === ACCUMULATION PHASES (bullish) ===

    # Phase E Accumulation: Markup - breakout, strong uptrend
    if (trend_30d > acc_cfg.phase_e.trend_30d and
        trend_7d > acc_cfg.phase_e.trend_7d and
        position_in_range > acc_cfg.phase_e.position_in_range):
        return "Accumulation Phase E", scores_cfg.accumulation_phase_e

    # Phase D Accumulation: Sign of strength - higher lows, grinding up
    if (trend_30d > acc_cfg.phase_d.trend_30d and
        trend_7d > acc_cfg.phase_d.trend_7d and
        position_in_range > acc_cfg.phase_d.position_in_range):
        return "Accumulation Phase D", scores_cfg.accumulation_phase_d

    # Phase C Accumulation: Spring - near lows, volatility spike, reversal starting
    if (position_in_range < acc_cfg.phase_c.position_in_range and
        trend_7d > acc_cfg.phase_c.trend_7d and
        vol_ratio > acc_cfg.phase_c.vol_ratio):
        return "Accumulation Phase C", scores_cfg.accumulation_phase_c

    # Phase B→C: Transitioning from consolidation to spring
    if (position_in_range < acc_cfg.phase_b_to_c.position_max and
        position_in_range > acc_cfg.phase_b_to_c.position_min and
        abs(trend_30d) < acc_cfg.phase_b_to_c.trend_30d_abs):
        if trend_7d > 0:
            return "Accumulation Phase B→C", scores_cfg.accumulation_phase_b_to_c
        else:
            return "Accumulation Phase B", scores_cfg.accumulation_phase_b

    # Phase B Accumulation: Building cause - sideways consolidation
    if abs(trend_30d) < acc_cfg.phase_b.trend_30d_abs and vol_ratio < acc_cfg.phase_b.vol_ratio:
        if position_in_range < acc_cfg.phase_b.position_in_range:
            return "Accumulation Phase B", scores_cfg.accumulation_phase_b - 2  # 58
        else:
            return "Re-accumulation", scores_cfg.re_accumulation

    # Phase A Accumulation: Selling climax - sharp decline finding support
    if (pct_from_high > acc_cfg.phase_a.pct_from_high and
        trend_7d > acc_cfg.phase_a.trend_7d and
        trend_30d < acc_cfg.phase_a.trend_30d):
        return "Accumulation Phase A", scores_cfg.accumulation_phase_a

    # === NEUTRAL/TRANSITIONAL ===

    # Markup trend (bullish continuation)
    if trend_30d > wyckoff_cfg.markup_trend_30d and position_in_range > 0.6:
        return "Markup", scores_cfg.markup

    # Markdown trend (bearish continuation)
    if trend_30d < wyckoff_cfg.markdown_trend_30d and position_in_range < 0.4:
        return "Markdown", scores_cfg.markdown

    # Ranging/unclear
    if abs(trend_30d) < wyckoff_cfg.range_trend_30d:
        if position_in_range > 0.5:
            return "Range (upper)", scores_cfg.range_upper
        else:
            return "Range (lower)", scores_cfg.range_lower

    # Default fallback
    if trend_30d > 0:
        return "Uptrend", scores_cfg.uptrend
    else:
        return "Downtrend", scores_cfg.downtrend


def get_wyckoff_score(phase: str) -> int:
    """
    Get a normalized Wyckoff score (0-100) from phase string.

    Used for backward compatibility with manual phase overrides.
    Scores are loaded from config.yaml.
    """
    scores_cfg = config.wyckoff.scores
    phase_lower = phase.lower()

    # Re-accumulation (must check before "accumulation")
    if "re-accumulation" in phase_lower:
        return scores_cfg.re_accumulation

    # Distribution phases (bearish)
    if "distribution" in phase_lower:
        if "phase e" in phase_lower or "markdown" in phase_lower:
            return scores_cfg.distribution_phase_e
        elif "phase d" in phase_lower:
            return scores_cfg.distribution_phase_d
        elif "phase c" in phase_lower:
            return scores_cfg.distribution_phase_c
        elif "phase b" in phase_lower:
            return scores_cfg.distribution_phase_b
        elif "phase a" in phase_lower:
            return scores_cfg.distribution_phase_a
        return scores_cfg.distribution_default

    # Accumulation phases (bullish) - scores aligned with detect_wyckoff_phase
    # Note: Only match "accumulation", not generic "phase" (which would match distribution phases)
    if "accumulation" in phase_lower:
        if "phase e" in phase_lower or "markup" in phase_lower:
            return scores_cfg.accumulation_phase_e
        elif "phase d" in phase_lower:
            return scores_cfg.accumulation_phase_d
        elif "b→c" in phase_lower or "b->c" in phase_lower:
            return scores_cfg.accumulation_phase_b_to_c
        elif "phase c" in phase_lower:
            return scores_cfg.accumulation_phase_c
        elif "phase b" in phase_lower:
            return scores_cfg.accumulation_phase_b
        elif "phase a" in phase_lower:
            return scores_cfg.accumulation_phase_a
        return scores_cfg.accumulation_default

    # Other phases
    if "markup" in phase_lower:
        return scores_cfg.markup
    if "markdown" in phase_lower:
        return scores_cfg.markdown
    if "range" in phase_lower:
        if "upper" in phase_lower:
            return scores_cfg.range_upper
        elif "lower" in phase_lower:
            return scores_cfg.range_lower
        return scores_cfg.range_default
    if "uptrend" in phase_lower:
        return scores_cfg.uptrend
    if "downtrend" in phase_lower:
        return scores_cfg.downtrend
    if "pre-market" in phase_lower:
        return scores_cfg.default

    return scores_cfg.default  # Default neutral
