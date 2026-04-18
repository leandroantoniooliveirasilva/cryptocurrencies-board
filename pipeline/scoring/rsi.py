"""RSI (Relative Strength Index) calculation using Wilder's smoothing."""

import logging
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)


def compute_rsi(prices: list[float], period: int = 14) -> Optional[float]:
    """
    Calculate RSI using Wilder's smoothing method.

    Args:
        prices: List of closing prices (oldest to newest)
        period: RSI period (default 14)

    Returns:
        RSI value (0-100) or None if insufficient or invalid data
    """
    if len(prices) < period + 1:
        return None

    # Validate prices contain no None/NaN values
    prices_array = np.array(prices, dtype=float)
    if np.any(np.isnan(prices_array)):
        logger.warning(f"RSI rejected: {np.sum(np.isnan(prices_array))} NaN values in price data")
        return None
    if np.any(prices_array <= 0):
        min_price = np.min(prices_array)
        zero_count = np.sum(prices_array <= 0)
        logger.warning(f"RSI rejected: {zero_count} prices <= 0 (min: {min_price:.6f})")
        return None

    deltas = np.diff(prices_array)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    # Initial averages
    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))

    # Wilder's smoothing for remaining periods
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    # Handle edge cases for division
    if avg_loss == 0:
        # If no losses but also no gains (flat price), return neutral RSI
        if avg_gain == 0:
            return 50.0
        # Only gains, no losses = fully overbought
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return round(rsi, 1)
