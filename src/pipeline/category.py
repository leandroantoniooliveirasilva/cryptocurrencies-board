"""Asset category resolution and scoring helpers (9-category taxonomy)."""

from typing import Any, Optional

# Legacy asset_type → asset_category (when asset_category omitted in YAML)
LEGACY_ASSET_TYPE_TO_CATEGORY: dict[str, str] = {
    'store-of-value': 'monetary-store-of-value',
    'smart-contract': 'smart-contract-platform',
    'defi': 'defi-protocol',
}


def resolve_asset_category(entry: dict[str, Any]) -> str:
    """
    Resolve asset_category from config entry.

    Prefer explicit asset_category; else map legacy asset_type; else default.
    """
    explicit = entry.get('asset_category')
    if explicit:
        return str(explicit)
    legacy = entry.get('asset_type')
    if legacy and legacy in LEGACY_ASSET_TYPE_TO_CATEGORY:
        return LEGACY_ASSET_TYPE_TO_CATEGORY[legacy]
    return 'default'


def weights_include(weights: dict[str, float], key: str) -> bool:
    return key in weights and weights[key] and weights[key] > 0


def should_score_value_capture(weights: dict[str, float], fee_model: Optional[str]) -> bool:
    """Value capture dimension is scored only when weighted and fee_model allows."""
    if not weights_include(weights, 'value_capture'):
        return False
    if fee_model in ('miner', 'minimal', 'equity'):
        return False
    return True


def should_score_adoption_activity(weights: dict[str, float]) -> bool:
    return weights_include(weights, 'adoption_activity')


def value_capture_skip_rationale(fee_model: Optional[str]) -> Optional[str]:
    if fee_model == 'miner':
        return (
            'Fee model routes fees to miners/validators without holder accrual. '
            'Value capture excluded; security budget read under Supply.'
        )
    if fee_model == 'minimal':
        return 'Fees minimal by design. Value capture excluded for this asset.'
    if fee_model == 'equity':
        return 'Revenue accrues to equity, not token. Value capture excluded.'
    return None


def adoption_hint_for_category(asset_category: str) -> str:
    """Short context string for LLM adoption scoring."""
    hints = {
        'smart-contract-platform': 'L1/L2 usage: active addresses, TPS, DeFi TVL, dev activity.',
        'defi-protocol': 'DeFi usage: TVL trend, users, integrations, volume.',
        'oracle-data': 'Oracle adoption: TVS, integrations, data-stream / CCIP usage.',
        'enterprise-settlement': 'Enterprise activity: TPS, tx/day, validators, institutional wallets.',
        'payments-rail': 'Payments: ODL/corridor volume, stablecoin flows, partnerships.',
        'shared-security': 'Restaking: AVS count, operators, restaked TVL.',
        'data-availability-modular': 'DA usage: rollups served, bytes posted, DA fees.',
        'ai-compute-depin': 'DePIN/AI: subnet usage, compute supply/demand, deployments.',
        'default': 'Network and usage adoption relevant to this asset class.',
    }
    return hints.get(asset_category, hints['default'])
