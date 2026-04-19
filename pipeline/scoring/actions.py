"""Action state derivation logic."""

from typing import Optional

from pipeline.config import config


def derive_action(
    composite: int,
    composite_last_week: int,
    tier: str,
    wyckoff_phase: str,
    trend_7d: list[int],
    trend_30d: list[int],
    rsi_daily: Optional[float],
    rsi_weekly: Optional[float],
    rsi_weekly_4w_ago: Optional[float] = None,
    gli_downtrend: bool = False,
    rs_underperforming: bool = False,
) -> str:
    """
    Derive action state based on scores and indicators.

    Action states:
    - strong-accumulate: True capitulation only — both weekly AND daily RSI <30 (leader only)
    - accumulate: Tranche-eligible zone (leader only)
    - promote: Runner-up crossing leader threshold
    - hold: Active position, no action signal (leader default)
    - await: Signal building, not yet activated (runner-up default)
    - observe: Observation tier only (observation default)
    - stand-aside: Distribution risk or negative structural trend

    Accumulation triggers (leaders only):
    1. Strong-accumulate: Weekly RSI <30 AND Daily RSI <30 (true capitulation, 82.9% hit rate)
    2. Strong-accumulate: Wyckoff Phase C + daily flush + weekly RSI stable/rising (not falling from high)
    3. Accumulate: Weekly RSI <30 alone, OR Wyckoff dip with weekly falling from high

    Filters:
    - GLI (Global Liquidity Index): When contracting, strong-accumulate downgrades to accumulate
    - RS vs BTC: When asset is underperforming BTC, strong-accumulate downgrades to accumulate
    - Weekly RSI slope: If weekly RSI is falling from elevated levels (>55), downgrade to accumulate
      This catches "first leg down" scenarios where daily flushes but weekly is breaking down

    All thresholds are configured in config.yaml.

    Args:
        composite: Current composite score
        composite_last_week: Composite score from 7 days ago
        tier: Asset tier ('leader', 'runner-up', 'observation')
        wyckoff_phase: Current Wyckoff phase string
        trend_7d: Last 7 days of composite scores
        trend_30d: Last 30 days of composite scores
        rsi_daily: Daily RSI(14) or None
        rsi_weekly: Weekly RSI(14) or None
        rsi_weekly_4w_ago: Weekly RSI from 4 weeks ago (for slope check) or None
        gli_downtrend: True if Global Liquidity Index is contracting
        rs_underperforming: True if asset is underperforming BTC over lookback period

    Returns:
        Action state string
    """
    # Load thresholds from config
    rsi_cfg = config.rsi
    comp_cfg = config.composite
    promo_cfg = config.promotion

    # Calculate deltas
    delta = _weekly_delta(trend_7d)
    delta_30 = _monthly_delta(trend_30d)
    phase_lower = wyckoff_phase.lower() if wyckoff_phase else ""

    # Stand Aside overrides everything - structural break
    if "distribution" in phase_lower and delta < 0:
        return "stand-aside"
    if delta <= comp_cfg.stand_aside_delta:
        return "stand-aside"

    if tier == "leader":
        # === CAPITULATION SIGNALS (RSI-based, independent of Wyckoff) ===
        # Extreme oversold on quality assets = buying opportunity
        # Leaders have proven fundamentals, so deep RSI readings represent
        # panic/capitulation that quality assets typically recover from.
        weekly_capitulation = rsi_weekly is not None and rsi_weekly < rsi_cfg.capitulation_weekly
        daily_capitulation = rsi_daily is not None and rsi_daily < rsi_cfg.capitulation_daily

        if weekly_capitulation:
            # Both daily AND weekly deeply oversold = strong capitulation
            if daily_capitulation:
                # GLI filter: downgrade strong-accumulate when liquidity contracting
                if gli_downtrend:
                    return "accumulate"
                # RS filter: downgrade when asset is underperforming BTC
                if rs_underperforming:
                    return "accumulate"
                return "strong-accumulate"
            # Weekly deeply oversold alone = accumulate signal
            return "accumulate"

        # === WYCKOFF-BASED ACCUMULATION (structural) ===
        # Check for Phase C or B→C (spring/transition zones)
        # Must exclude distribution phases (UTAD) which share the "phase c"
        # substring but are bearish, not bullish.
        is_distribution = "distribution" in phase_lower
        wyckoff_ready = (not is_distribution) and (
            "phase c" in phase_lower or
            "→c" in phase_lower or
            "->c" in phase_lower
        )
        overbought = rsi_weekly is not None and rsi_weekly >= rsi_cfg.overbought_weekly
        accumulate_regime = (
            composite >= comp_cfg.accumulate_threshold and
            wyckoff_ready and
            delta >= 0 and
            not overbought
        )

        if accumulate_regime:
            # Wyckoff-based accumulation: daily flush with weekly intact
            # Check if this qualifies for strong-accumulate or regular accumulate
            composite_stable = (composite - composite_last_week) >= comp_cfg.stability_tolerance
            daily_oversold = rsi_daily is not None and rsi_daily <= rsi_cfg.oversold_daily
            weekly_intact = rsi_weekly is not None and rsi_weekly >= rsi_cfg.intact_weekly

            if daily_oversold and weekly_intact and composite_stable:
                # Check weekly RSI slope - is it falling from elevated levels?
                # If weekly was >55 and has dropped significantly, this is likely
                # the first leg of a correction, not a buyable dip.
                weekly_falling_from_high = (
                    rsi_weekly_4w_ago is not None and
                    rsi_weekly_4w_ago > rsi_cfg.slope_high_threshold and
                    rsi_weekly < rsi_weekly_4w_ago - rsi_cfg.slope_drop_threshold
                )

                if weekly_falling_from_high:
                    # Weekly momentum breaking down from overbought - not a strong signal
                    # Backtest: 2021 April/May/Dec crashes all had this pattern
                    return "accumulate"

                # GLI filter: downgrade strong-accumulate when liquidity contracting
                if gli_downtrend:
                    return "accumulate"

                # RS filter: downgrade when asset is underperforming BTC
                if rs_underperforming:
                    return "accumulate"

                return "strong-accumulate"

            return "accumulate"

        return "hold"

    if tier == "runner-up":
        if (composite >= promo_cfg.composite_threshold and
            delta_30 >= promo_cfg.delta_30d and
            delta >= promo_cfg.delta_7d):
            return "promote"
        return "await"

    return "observe"


def _weekly_delta(trend: list) -> int:
    """Calculate 7-day delta from trend array."""
    if not trend or len(trend) < 2:
        return 0
    first, last = trend[0], trend[-1]
    # Guard against None or non-numeric values
    if not isinstance(first, (int, float)) or not isinstance(last, (int, float)):
        return 0
    return last - first


def _monthly_delta(trend: list) -> int:
    """Calculate 30-day delta from trend array."""
    if not trend or len(trend) < 2:
        return 0
    first, last = trend[0], trend[-1]
    # Guard against None or non-numeric values
    if not isinstance(first, (int, float)) or not isinstance(last, (int, float)):
        return 0
    return last - first
