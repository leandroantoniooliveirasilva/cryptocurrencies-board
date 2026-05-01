"""Action state derivation logic."""

from typing import Any, Optional

from pipeline.config import config


_DOWNGRADE_REASON_COPY = {
    'macro:gli_contracting': 'global liquidity is contracting',
    'macro:rs_underperforming_btc': 'relative strength vs BTC is weak',
    'macro:fear_greed_euphoria': 'market sentiment is euphoric',
    'wyckoff:markup': 'Wyckoff structure is already in markup',
    'wyckoff:distribution_or_markdown': 'Wyckoff structure is distribution/markdown',
}


_ACTION_COPY = {
    'strong-accumulate': 'Strong Accumulate',
    'accumulate': 'Accumulate',
    'hold': 'Hold',
    'await': 'Await Confirmation',
    'promote': 'Promote Candidate',
    'observe': 'Observe',
    'stand-aside': 'Stand Aside',
}


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
    fg_greedy: bool = False,
    weekly_averages: Optional[list[dict]] = None,
) -> tuple[str, dict[str, Any]]:
    """
    Derive action state based on scores and indicators.

    Args:
        weekly_averages: Optional list of weekly composite averages from
            get_weekly_composite_averages(). Used for stand-aside logic.

    Returns:
        Tuple of (action string, decision_trace dict for auditing and UI).
    """
    macro_reasons: list[str] = []
    if gli_downtrend:
        macro_reasons.append('macro:gli_contracting')
    if rs_underperforming:
        macro_reasons.append('macro:rs_underperforming_btc')
    if fg_greedy:
        macro_reasons.append('macro:fear_greed_euphoria')

    macro_downgrade_active = gli_downtrend or rs_underperforming or fg_greedy

    rsi_cfg = config.rsi
    comp_cfg = config.composite
    promo_cfg = config.promotion

    delta = _weekly_delta(trend_7d)
    delta_30 = _monthly_delta(trend_30d)
    phase_lower = wyckoff_phase.lower() if wyckoff_phase else ''
    is_distribution = bool('distribution' in phase_lower)

    common_inputs: dict[str, Any] = {
        'tier': tier,
        'composite': composite,
        'composite_last_week': composite_last_week,
        'delta_7d': delta,
        'delta_30d': delta_30,
        'wyckoff_phase': wyckoff_phase or '',
        'is_distribution': is_distribution,
        'macro_downgrade_active': bool(macro_downgrade_active),
        'macro_reasons': list(macro_reasons),
        'stand_aside_delta_threshold': comp_cfg.stand_aside_delta,
    }

    # Stand Aside overrides everything - structural break
    # Requires 5+ weeks of weekly averages to ensure reliable signal
    # (no stand-aside during initial calibration period)
    if (weekly_averages
        and len(weekly_averages) >= comp_cfg.stand_aside_weeks_required
        and len(weekly_averages) > comp_cfg.stand_aside_lookback_weeks):

        latest_week = weekly_averages[0]
        lookback_weeks = comp_cfg.stand_aside_lookback_weeks
        comparison_week = weekly_averages[lookback_weeks]
        weekly_delta = latest_week['avg_composite'] - comparison_week['avg_composite']

        if weekly_delta <= comp_cfg.stand_aside_delta:
            return 'stand-aside', _make_trace(
                path='stand_aside_sharp_decline',
                final_action='stand-aside',
                summary=(
                    f'Stand-aside: {lookback_weeks}-week composite trend ({weekly_delta:.1f}) '
                    f'<= threshold ({comp_cfg.stand_aside_delta}). '
                    f'Latest week avg: {latest_week["avg_composite"]:.1f} '
                    f'({latest_week["week_id"]}, {latest_week["snapshot_count"]} runs); '
                    f'{lookback_weeks} weeks ago: {comparison_week["avg_composite"]:.1f} '
                    f'({comparison_week["week_id"]}). Structural break detected.'
                ),
                inputs={
                    **common_inputs,
                    'rule': f'weekly_avg_delta_{lookback_weeks}w <= composite.stand_aside_delta',
                    'latest_week': latest_week['week_id'],
                    'latest_avg': latest_week['avg_composite'],
                    'comparison_week': comparison_week['week_id'],
                    'comparison_avg': comparison_week['avg_composite'],
                    'weekly_delta': weekly_delta,
                },
            )

    if tier == 'leader':
        weekly_capitulation = bool(rsi_weekly is not None and rsi_weekly < rsi_cfg.capitulation_weekly)
        daily_capitulation = bool(rsi_daily is not None and rsi_daily < rsi_cfg.capitulation_daily)

        leader_inputs = {
            **common_inputs,
            'rsi_daily': rsi_daily,
            'rsi_weekly': rsi_weekly,
            'rsi_weekly_4w_ago': rsi_weekly_4w_ago,
            'weekly_capitulation': weekly_capitulation,
            'daily_capitulation': daily_capitulation,
        }

        if weekly_capitulation:
            if daily_capitulation:
                base = 'strong-accumulate'
                final, dg = _apply_downgrades(
                    base, wyckoff_phase, macro_downgrade_active, macro_reasons,
                )
                return final, _make_trace(
                    path='leader_capitulation_both_rsi',
                    final_action=final,
                    base_action=base,
                    downgrades=dg,
                    summary=_accumulation_summary(base, final, dg, 'RSI weekly+daily capitulation'),
                    inputs={
                        **leader_inputs,
                        'path_detail': 'weekly RSI < capitulation_weekly and daily RSI < capitulation_daily',
                    },
                )

            base = 'accumulate'
            final, dg = _apply_downgrades(
                base, wyckoff_phase, macro_downgrade_active, macro_reasons,
            )
            return final, _make_trace(
                path='leader_capitulation_weekly_only',
                final_action=final,
                base_action=base,
                downgrades=dg,
                summary=_accumulation_summary(base, final, dg, 'RSI weekly capitulation only'),
                inputs={
                    **leader_inputs,
                    'path_detail': 'weekly RSI < capitulation_weekly; daily not confirmed',
                },
            )

        wyckoff_ready = bool((not is_distribution) and (
            'phase c' in phase_lower or
            '→c' in phase_lower or
            '->c' in phase_lower
        ))
        overbought = bool(rsi_weekly is not None and rsi_weekly >= rsi_cfg.overbought_weekly)
        accumulate_regime = bool(
            composite >= comp_cfg.accumulate_threshold and
            wyckoff_ready and
            delta >= 0 and
            not overbought
        )

        wyckoff_inputs = {
            **leader_inputs,
            'wyckoff_ready': wyckoff_ready,
            'overbought_weekly': overbought,
            'accumulate_regime': accumulate_regime,
            'accumulate_threshold': comp_cfg.accumulate_threshold,
        }

        if accumulate_regime:
            composite_stable = bool((composite - composite_last_week) >= comp_cfg.stability_tolerance)
            daily_oversold = bool(rsi_daily is not None and rsi_daily <= rsi_cfg.oversold_daily)
            weekly_intact = bool(rsi_weekly is not None and rsi_weekly >= rsi_cfg.intact_weekly)

            if daily_oversold and weekly_intact and composite_stable:
                weekly_falling_from_high = bool(
                    rsi_weekly is not None and
                    rsi_weekly_4w_ago is not None and
                    rsi_weekly_4w_ago > rsi_cfg.slope_high_threshold and
                    rsi_weekly < rsi_weekly_4w_ago - rsi_cfg.slope_drop_threshold
                )

                if weekly_falling_from_high:
                    base = 'accumulate'
                    final, dg = _apply_downgrades(
                        base, wyckoff_phase, macro_downgrade_active, macro_reasons,
                    )
                    return final, _make_trace(
                        path='leader_wyckoff_weekly_slope_downgrade',
                        final_action=final,
                        base_action=base,
                        downgrades=dg,
                        summary=_accumulation_summary(
                            base, final, dg,
                            'Wyckoff dip setup but weekly RSI falling from elevated zone',
                        ),
                        inputs={
                            **wyckoff_inputs,
                            'composite_stable': composite_stable,
                            'daily_oversold': daily_oversold,
                            'weekly_intact': weekly_intact,
                            'weekly_falling_from_high': True,
                            'rule': 'slope_high_threshold / slope_drop_threshold',
                        },
                    )

                base = 'strong-accumulate'
                final, dg = _apply_downgrades(
                    base, wyckoff_phase, macro_downgrade_active, macro_reasons,
                )
                return final, _make_trace(
                    path='leader_wyckoff_strong_accumulate',
                    final_action=final,
                    base_action=base,
                    downgrades=dg,
                    summary=_accumulation_summary(
                        base, final, dg,
                        'Wyckoff spring/phase-C style: daily oversold, weekly intact, composite stable',
                    ),
                    inputs={
                        **wyckoff_inputs,
                        'composite_stable': composite_stable,
                        'daily_oversold': daily_oversold,
                        'weekly_intact': weekly_intact,
                        'weekly_falling_from_high': False,
                    },
                )

            base = 'accumulate'
            final, dg = _apply_downgrades(
                base, wyckoff_phase, macro_downgrade_active, macro_reasons,
            )
            return final, _make_trace(
                path='leader_wyckoff_accumulate',
                final_action=final,
                base_action=base,
                downgrades=dg,
                summary=_accumulation_summary(
                    base, final, dg,
                    'Wyckoff accumulation regime (composite + phase + trend gates passed)',
                ),
                inputs=wyckoff_inputs,
            )

        return 'hold', _make_trace(
            path='leader_hold_default',
            final_action='hold',
            summary=(
                'Hold: leader-tier asset remains active, but no accumulation trigger is currently confirmed '
                '(no RSI capitulation and no active Wyckoff accumulation regime).'
            ),
            inputs=wyckoff_inputs,
        )

    if tier == 'runner-up':
        if (composite >= promo_cfg.composite_threshold and
                delta_30 >= promo_cfg.delta_30d and
                delta >= promo_cfg.delta_7d):
            return 'promote', _make_trace(
                path='runner_up_promote',
                final_action='promote',
                summary=(
                    f'Promote: composite >= {promo_cfg.composite_threshold}, '
                    f'30d delta >= {promo_cfg.delta_30d}, 7d delta >= {promo_cfg.delta_7d}.'
                ),
                inputs={
                    **common_inputs,
                    'promotion_composite_threshold': promo_cfg.composite_threshold,
                    'promotion_delta_30d': promo_cfg.delta_30d,
                    'promotion_delta_7d': promo_cfg.delta_7d,
                },
            )
        return 'await', _make_trace(
            path='runner_up_await',
            final_action='await',
            summary='Await: runner-up quality is improving, but promotion thresholds are not yet met.',
            inputs=common_inputs,
        )

    return 'observe', _make_trace(
        path='observe_default',
        final_action='observe',
        summary='Observe: research/watchlist state only; no active accumulation signal.',
        inputs=common_inputs,
    )


def _make_trace(
    path: str,
    final_action: str,
    summary: str,
    *,
    base_action: Optional[str] = None,
    downgrades: Optional[dict[str, Any]] = None,
    inputs: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        'path': path,
        'final_action': final_action,
        'summary': summary,
    }
    if base_action is not None:
        out['base_action'] = base_action
    if downgrades is not None:
        out['downgrades'] = downgrades
    if inputs is not None:
        out['inputs'] = inputs
    return out


def _accumulation_summary(
    base_action: str,
    final_action: str,
    downgrades: dict[str, Any],
    trigger: str,
) -> str:
    base_label = _ACTION_COPY.get(base_action, base_action)
    final_label = _ACTION_COPY.get(final_action, final_action)
    parts = [f'Base signal: {base_label} ({trigger}).']
    if final_action != base_action:
        lv = downgrades.get('levels_applied', 0)
        reasons = downgrades.get('reasons', [])
        reason_txt = _format_downgrade_reasons(reasons)
        parts.append(f'After {lv} downgrade level(s) ({reason_txt}): {final_label}.')
    else:
        parts.append('No accumulation downgrades applied.')
    return ' '.join(parts)


def _format_downgrade_reasons(reasons: list[str]) -> str:
    if not reasons:
        return 'macro/Wyckoff filters'
    readable = [_DOWNGRADE_REASON_COPY.get(reason, reason) for reason in reasons]
    return '; '.join(readable)


def _apply_downgrades(
    action: str,
    wyckoff_phase: str,
    macro_downgrade_active: bool,
    macro_reasons: list[str],
) -> tuple[str, dict[str, Any]]:
    """Apply macro and Wyckoff downgrades to accumulation signals."""
    if action not in {'strong-accumulate', 'accumulate'}:
        return action, {}

    macro_levels = 1 if macro_downgrade_active else 0
    wy_levels = _wyckoff_downgrade_levels(wyckoff_phase)
    total_levels = macro_levels + wy_levels

    reasons: list[str] = []
    if macro_downgrade_active:
        reasons.extend(macro_reasons)
    wy_reason = _wyckoff_downgrade_reason(wyckoff_phase)
    if wy_reason:
        reasons.append(wy_reason)

    final = _downgrade_action(action, total_levels)
    return final, {
        'base_action': action,
        'levels_applied': total_levels,
        'macro_levels': macro_levels,
        'wyckoff_levels': wy_levels,
        'reasons': reasons,
    }


def _wyckoff_downgrade_reason(wyckoff_phase: str) -> Optional[str]:
    phase = (wyckoff_phase or '').lower()
    if 'markdown' in phase or 'distribution' in phase:
        return 'wyckoff:distribution_or_markdown'
    if 'markup' in phase:
        return 'wyckoff:markup'
    return None


def _wyckoff_downgrade_levels(wyckoff_phase: str) -> int:
    """
    Convert Wyckoff phase into downgrade levels.

    accumulation: 0, markup: 1, distribution/markdown: 2.
    """
    phase = (wyckoff_phase or '').lower()
    if 'markdown' in phase or 'distribution' in phase:
        return 2
    if 'markup' in phase:
        return 1
    return 0


def _downgrade_action(action: str, levels: int) -> str:
    """Downgrade action by N levels within accumulation states."""
    state_order = ['strong-accumulate', 'accumulate', 'hold']
    idx = state_order.index(action)
    next_idx = min(idx + max(levels, 0), len(state_order) - 1)
    return state_order[next_idx]


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
