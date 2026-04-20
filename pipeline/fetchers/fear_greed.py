"""Fear & Greed Index fetcher.

Fetches the Bitcoin Fear & Greed Index from Alternative.me API.
Used as a sentiment filter to downgrade accumulation signals during extreme greed.
"""

import logging
from typing import Optional
import requests

from pipeline.config import config

logger = logging.getLogger(__name__)

# Alternative.me API endpoint (free, no auth required)
FEAR_GREED_API = "https://api.alternative.me/fng/"


def fetch_fear_greed() -> dict:
    """
    Fetch current Fear & Greed Index.

    Returns:
        Dict with:
        - value: int (0-100)
        - classification: str ("Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed")
        - timestamp: str (ISO format)
        - greedy: bool (True if value >= threshold, triggers downgrade)
    """
    fg_cfg = getattr(config, 'fear_greed', None)

    # Check if F&G filter is enabled
    if fg_cfg and not fg_cfg.enabled:
        return {
            "enabled": False,
            "value": None,
            "classification": None,
            "greedy": False,
        }

    threshold = fg_cfg.threshold if fg_cfg else 70

    try:
        response = requests.get(
            FEAR_GREED_API,
            params={"limit": 1, "format": "json"},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        if "data" not in data or len(data["data"]) == 0:
            logger.warning("Fear & Greed API returned no data")
            return _fallback_result()

        fg_data = data["data"][0]
        value = int(fg_data.get("value", 50))
        classification = fg_data.get("value_classification", "Neutral")
        timestamp = fg_data.get("timestamp")

        greedy = value >= threshold

        if greedy:
            logger.info(f"Fear & Greed at {value} ({classification}) - above threshold {threshold}, downgrades active")
        else:
            logger.debug(f"Fear & Greed at {value} ({classification})")

        return {
            "enabled": True,
            "value": value,
            "classification": classification,
            "timestamp": timestamp,
            "threshold": threshold,
            "greedy": greedy,
        }

    except requests.RequestException as e:
        logger.warning(f"Failed to fetch Fear & Greed Index: {e}")
        return _fallback_result()


def _fallback_result() -> dict:
    """Return neutral fallback when API fails."""
    return {
        "enabled": True,
        "value": None,
        "classification": None,
        "greedy": False,  # Don't trigger downgrade on failure
        "error": "API unavailable",
    }
