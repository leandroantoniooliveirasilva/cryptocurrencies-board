"""Composite score calculation with tiered weights by asset type.

Asset types and their weight profiles:
- store-of-value: Institutional-heavy (BTC, KAS)
- smart-contract: Balanced (SOL, AVAX, ETH)
- defi: Revenue-heavy (LINK, AAVE, MORPHO, HYPE)
- infrastructure: Institutional + Regulatory (QNT, XLM, XRP, HBAR)

Dimensions:
- institutional: ETF flows, fund holdings, custody adoption
- revenue: Protocol fees, sustainable revenue
- regulatory: Jurisdictional clarity, ETF approval status
- supply: Exchange reserves, holder distribution, inflation
- wyckoff: Technical phase (accumulation/distribution)
"""

from typing import Optional

# Tiered weights by asset type
WEIGHTS_BY_TYPE = {
    "store-of-value": {
        "institutional": 0.40,
        "supply": 0.25,
        "regulatory": 0.15,
        "wyckoff": 0.15,
        "revenue": 0.05,
    },
    "smart-contract": {
        "institutional": 0.30,
        "revenue": 0.25,
        "supply": 0.20,
        "regulatory": 0.15,
        "wyckoff": 0.10,
    },
    "defi": {
        "revenue": 0.35,
        "institutional": 0.25,
        "regulatory": 0.20,
        "supply": 0.15,
        "wyckoff": 0.05,
    },
    "infrastructure": {
        "institutional": 0.35,
        "regulatory": 0.25,
        "supply": 0.20,
        "revenue": 0.10,
        "wyckoff": 0.10,
    },
}

# Default weights (balanced) for unknown asset types
DEFAULT_WEIGHTS = {
    "institutional": 0.30,
    "revenue": 0.20,
    "regulatory": 0.20,
    "supply": 0.20,
    "wyckoff": 0.10,
}

# Legacy weights for backward compatibility
WEIGHTS = DEFAULT_WEIGHTS


def get_weights(asset_type: Optional[str] = None) -> dict:
    """
    Get weight profile for an asset type.

    Args:
        asset_type: One of 'store-of-value', 'smart-contract', 'defi', 'infrastructure'

    Returns:
        Dict of dimension weights summing to 1.0
    """
    if asset_type and asset_type in WEIGHTS_BY_TYPE:
        return WEIGHTS_BY_TYPE[asset_type]
    return DEFAULT_WEIGHTS


def compute_composite(
    scores: dict,
    asset_type: Optional[str] = None,
) -> tuple[int, int]:
    """
    Compute weighted composite score from dimension scores.

    Missing/None values are excluded and weights are renormalized.
    This ensures scores are resilient to incomplete data rather than
    assuming neutral (50) for unavailable dimensions.

    Args:
        scores: Dict with keys 'institutional', 'revenue', 'regulatory', 'supply', 'wyckoff'
                Each value should be 0-100 or None for missing data.
        asset_type: Asset type for weight selection

    Returns:
        Tuple of (rounded composite score 0-100, count of missing dimensions)
    """
    weights = get_weights(asset_type)

    total = 0.0
    total_weight = 0.0
    missing_count = 0

    for dimension, weight in weights.items():
        score = scores.get(dimension)
        # Only include dimensions with valid scores (not None, not NaN)
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
        scores: Dict with 'institutional', 'revenue', 'regulatory', 'wyckoff'

    Returns:
        Tuple of (rounded composite score 0-100, count of missing dimensions)
    """
    legacy_weights = {
        "institutional": 0.30,
        "revenue": 0.30,
        "regulatory": 0.25,
        "wyckoff": 0.15,
    }

    total = 0.0
    total_weight = 0.0
    missing_count = 0

    for dimension, weight in legacy_weights.items():
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


def explain_weights(asset_type: Optional[str] = None) -> str:
    """
    Return human-readable explanation of weights for an asset type.

    Args:
        asset_type: Asset type

    Returns:
        Formatted string explaining the weight profile
    """
    weights = get_weights(asset_type)
    type_name = asset_type or "default"

    lines = [f"Weight profile for {type_name}:"]
    for dim, weight in sorted(weights.items(), key=lambda x: -x[1]):
        lines.append(f"  {dim}: {int(weight * 100)}%")

    return "\n".join(lines)
