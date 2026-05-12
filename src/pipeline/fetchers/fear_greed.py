"""Fear & Greed Index fetcher.

Fetches the Bitcoin Fear & Greed Index from Alternative.me API.
Used as a sentiment filter to downgrade accumulation signals one level during extreme greed (same rule as GLI / RS filters).
"""

import logging
from typing import Optional

import requests

from pipeline.config import config

logger = logging.getLogger(__name__)

# Alternative.me API endpoint (free, no auth required)
FEAR_GREED_API = "https://api.alternative.me/fng/"


def fetch_fear_greed() -> Optional[dict]:
    """
    Fetch current Fear & Greed Index.

    Returns ``None`` when the API call fails so the caller can retry or reuse
    the previous run's value, instead of silently disabling the filter with a
    fabricated record.
    """
    fg_cfg = getattr(config, 'fear_greed', None)

    # Filter explicitly disabled in config — return the disabled record directly.
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
            return None

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
        return None


def fetch_fear_greed_with_retry(max_attempts: int = 3) -> Optional[dict]:
    """Retry ``fetch_fear_greed`` up to ``max_attempts`` times. Returns None if all fail."""
    for attempt in range(1, max_attempts + 1):
        data = fetch_fear_greed()
        if data is not None:
            return data
        logger.warning(f'Fear & Greed fetch attempt {attempt}/{max_attempts} failed')
    return None


def log_pipeline_summary(log: logging.Logger, fg_data: dict) -> None:
    """Same Fear & Greed log line for ``pipeline.run`` and ``pipeline.indicators``."""
    greedy = bool(fg_data.get('greedy'))
    if fg_data.get('enabled') and fg_data.get('value') is not None:
        cls = fg_data.get('classification') or 'unknown'
        log.info(
            f'Fear & Greed: {fg_data["value"]} ({cls}) - '
            f"{'GREEDY' if greedy else 'neutral'}"
        )
    else:
        log.info('Fear & Greed data unavailable - sentiment filter disabled')
