"""Composite score calculation with tiered weights by asset type.

Asset types and their weight profiles:
- store-of-value: Institutional-heavy (BTC, KAS)
- smart-contract: Balanced (SOL, AVAX, ETH)
- defi: Revenue-heavy (LINK, AAVE, MORPHO, HYPE)
- infrastructure: Institutional + Regulatory (QNT, XLM, XRP, HBAR)

Weighted dimensions (subset per asset category):
- institutional: ETF flows, fund holdings, custody adoption
- adoption_activity: Network usage (TVL, TPS, TVS, etc. — category-specific)
- value_capture: Holder-accruing fees / real yield (replaces flat “revenue”)
- regulatory: Jurisdictional clarity, ETF approval status
- supply: Exchange reserves, holder distribution, inflation, security budget

Wyckoff is not a weighted dimension; it is a daily-updated filter signal (see ``pipeline.indicators``).

All weight profiles are configured in config.yaml under weights_by_category.
"""

from typing import Optional

from pipeline.category import should_score_adoption_activity, should_score_value_capture
from pipeline.config import config


def get_weights(asset_category: Optional[str] = None) -> dict:
    """
    Get weight profile for an asset category from config.

    Args:
        asset_category: One of weights_by_category keys (e.g. defi-protocol)

    Returns:
        Dict of dimension weights summing to 1.0
    """
    return config.get_weights_for_category(asset_category or 'default')


# Export for dashboard (category → weights)
WEIGHTS_BY_TYPE = config.get_all_category_weights()


def compute_composite(
    scores: dict,
    asset_category: Optional[str] = None,
    fee_model: Optional[str] = None,
) -> tuple[int, int]:
    """
    Compute weighted composite from dimension scores.

    Only dimensions with **positive** weight in the category profile participate.
    Category rules skip ``value_capture`` or ``adoption_activity`` when those
    dimensions are not part of the framework for that asset (same rules as strict
    dimension checks in ``pipeline.run``).

    Valid scores contribute ``score * weight`` to the numerator; their weights sum
    to the denominator (implicit renormalisation over **scored** dimensions only).

    ``missing_dimensions`` counts dimensions that **would** contribute to the
    composite (positive weight, not skipped by category) but have no valid score
    (``None`` or NaN). It does not count excluded dimensions or zero-weight keys.

    Note: the weekly pipeline may raise ``DimensionScoringError`` before calling
    this when any required weighted dimension is missing; this function still
    supports callers that omit that strict gate.

    Args:
        scores: Dimension key → 0..100 or None.
        asset_category: Category for ``weights_by_category`` selection.
        fee_model: YAML ``fee_model``; used with weights to decide value-capture participation.

    Returns:
        ``(composite 0..100, missing_dimension_count)``.
    """
    weights = get_weights(asset_category)

    total = 0.0
    total_weight = 0.0
    missing_count = 0

    for dimension, weight in weights.items():
        if weight is None or float(weight) <= 0:
            continue
        if dimension == 'value_capture' and not should_score_value_capture(weights, fee_model):
            continue
        if dimension == 'adoption_activity' and not should_score_adoption_activity(weights):
            continue
        score = scores.get(dimension)
        if score is not None and (not isinstance(score, float) or not (score != score)):
            total += score * weight
            total_weight += weight
        else:
            missing_count += 1

    # Renormalize if we have any valid scores
    if total_weight > 0:
        composite = round(total / total_weight)
    else:
        # All dimensions missing - return neutral
        composite = 50

    return composite, missing_count


def compute_composite_legacy(scores: dict) -> tuple[int, int]:
    """
    Compute composite with legacy 4-dimension weights.
    For backward compatibility only.

    Args:
        scores: Dict with legacy keys 'institutional', 'revenue', 'regulatory' (Wyckoff excluded)

    Returns:
        Tuple of (rounded composite score 0-100, count of missing dimensions)
    """
    legacy_weights = {
        "institutional": 0.35,
        "revenue": 0.35,
        "regulatory": 0.30,
    }

    total = 0.0
    total_weight = 0.0
    missing_count = 0

    for dimension, weight in legacy_weights.items():
        if weight <= 0:
            continue
        score = scores.get(dimension)
        if score is not None and (not isinstance(score, float) or not (score != score)):
            total += score * weight
            total_weight += weight
        else:
            missing_count += 1

    if total_weight > 0:
        composite = round(total / total_weight)
    else:
        composite = 50

    return composite, missing_count


def explain_weights(asset_category: Optional[str] = None) -> str:
    """
    Return human-readable explanation of weights for an asset category.

    Args:
        asset_category: Asset category

    Returns:
        Formatted string explaining the weight profile
    """
    weights = get_weights(asset_category)
    type_name = asset_category or 'default'

    lines = [f"Weight profile for {type_name}:"]
    for dim, weight in sorted(weights.items(), key=lambda x: -x[1]):
        lines.append(f"  {dim}: {int(weight * 100)}%")

    return "\n".join(lines)
