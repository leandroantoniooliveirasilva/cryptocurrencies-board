"""On-chain data fetching (placeholder for future implementation)."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def fetch_exchange_reserves(symbol: str) -> Optional[dict]:
    """
    Fetch exchange reserve data for an asset.

    Note: This is a placeholder. Real implementation would use:
    - Glassnode API (paid)
    - CryptoQuant API
    - Santiment API
    - Direct blockchain queries

    Args:
        symbol: Asset symbol

    Returns:
        Dict with reserve metrics or None
    """
    # Placeholder - would integrate with on-chain data provider
    logger.debug(f"Exchange reserves fetch not implemented for {symbol}")
    return None


def fetch_flow_data(symbol: str) -> Optional[dict]:
    """
    Fetch exchange flow data (inflows/outflows).

    Note: Placeholder for future implementation.

    Args:
        symbol: Asset symbol

    Returns:
        Dict with flow metrics or None
    """
    logger.debug(f"Flow data fetch not implemented for {symbol}")
    return None


def compute_onchain_score(
    reserves: Optional[dict], flows: Optional[dict]
) -> Optional[int]:
    """
    Compute on-chain health score from reserve and flow data.

    Args:
        reserves: Exchange reserve data
        flows: Exchange flow data

    Returns:
        Score 0-100 or None if no data
    """
    if not reserves and not flows:
        return None

    # Placeholder scoring logic
    # Real implementation would consider:
    # - Exchange reserve trends (declining = bullish)
    # - Net flows (outflows = accumulation)
    # - Whale wallet movements
    # - Active addresses
    return 60  # Neutral placeholder
