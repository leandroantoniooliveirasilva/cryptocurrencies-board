"""Action state derivation logic."""

from typing import Optional


def derive_action(
    composite: int,
    composite_last_week: int,
    tier: str,
    wyckoff_phase: str,
    trend_7d: list[int],
    trend_30d: list[int],
    rsi_daily: Optional[float],
    rsi_weekly: Optional[float],
) -> str:
    """
    Derive action state based on scores and indicators.

    Action states:
    - strong-accumulate: Dislocation in accumulation zone OR capitulation (leader only)
    - accumulate: Tranche-eligible zone (leader only)
    - promote: Runner-up crossing leader threshold
    - hold: Active position, no action signal (leader default)
    - await: Signal building, not yet activated (runner-up default)
    - observe: Observation tier only (observation default)
    - stand-aside: Distribution risk or negative structural trend

    Accumulation triggers (leaders only):
    1. Wyckoff-based: Phase C/B→C + composite ≥75 + stable trend + weekly RSI <70
    2. Capitulation: Weekly RSI <30 (quality assets recover from panic selling)

    Args:
        composite: Current composite score
        composite_last_week: Composite score from 7 days ago
        tier: Asset tier ('leader', 'runner-up', 'observation')
        wyckoff_phase: Current Wyckoff phase string
        trend_7d: Last 7 days of composite scores
        trend_30d: Last 30 days of composite scores
        rsi_daily: Daily RSI(14) or None
        rsi_weekly: Weekly RSI(14) or None

    Returns:
        Action state string
    """
    # Calculate deltas
    delta = _weekly_delta(trend_7d)
    delta_30 = _monthly_delta(trend_30d)
    phase_lower = wyckoff_phase.lower() if wyckoff_phase else ""

    # Stand Aside overrides everything - structural break
    if "distribution" in phase_lower and delta < 0:
        return "stand-aside"
    if delta <= -5:
        return "stand-aside"

    if tier == "leader":
        # === CAPITULATION SIGNALS (RSI-based, independent of Wyckoff) ===
        # Extreme oversold on quality assets = buying opportunity
        # Leaders have proven fundamentals, so deep RSI readings represent
        # panic/capitulation that quality assets typically recover from.
        weekly_capitulation = rsi_weekly is not None and rsi_weekly < 30
        daily_capitulation = rsi_daily is not None and rsi_daily < 30

        if weekly_capitulation:
            # Both daily AND weekly deeply oversold = strong capitulation
            if daily_capitulation:
                return "strong-accumulate"
            # Weekly deeply oversold alone = accumulate signal
            return "accumulate"

        # === WYCKOFF-BASED ACCUMULATION (structural) ===
        # Check for Phase C or B→C (spring/transition zones)
        # Must be specific to avoid matching 'c' in 'accumulation'
        wyckoff_ready = (
            "phase c" in phase_lower or
            "→c" in phase_lower or
            "->c" in phase_lower
        )
        overbought = rsi_weekly is not None and rsi_weekly >= 70  # Conservative ceiling
        accumulate_regime = (
            composite >= 75 and wyckoff_ready and delta >= 0 and not overbought
        )

        if accumulate_regime:
            # Check Strong Accumulate conditions
            composite_stable = (composite - composite_last_week) >= -3
            daily_oversold = rsi_daily is not None and rsi_daily <= 32
            weekly_intact = rsi_weekly is not None and rsi_weekly >= 42

            if daily_oversold and weekly_intact and composite_stable:
                return "strong-accumulate"
            return "accumulate"

        return "hold"

    if tier == "runner-up":
        if composite >= 75 and delta_30 >= 8 and delta >= 2:
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
