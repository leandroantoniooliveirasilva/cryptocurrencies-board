"""
Centralized configuration loader for the Conviction Board pipeline.

All signal-critical thresholds and scoring parameters are defined in config.yaml
and accessed through this module. This ensures consistency and makes backtesting
parameter changes straightforward.

Usage:
    from pipeline.config import config

    # Access nested values
    threshold = config.rsi.capitulation_weekly
    weights = config.weights.get('defi')
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class ConfigSection:
    """
    A dict-like object that allows attribute access to nested config values.

    Supports both:
        config.rsi.capitulation_weekly
        config['rsi']['capitulation_weekly']
    """

    def __init__(self, data: dict):
        self._data = data
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, ConfigSection(value))
            else:
                setattr(self, key, value)

    def __getitem__(self, key: str) -> Any:
        value = self._data[key]
        if isinstance(value, dict):
            return ConfigSection(value)
        return value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value with optional default."""
        try:
            return self[key]
        except KeyError:
            return default

    def to_dict(self) -> dict:
        """Return the raw dict representation."""
        return self._data

    def __repr__(self) -> str:
        return f"ConfigSection({self._data})"


class Config:
    """
    Main configuration class that loads from config.yaml.

    Provides attribute-style access to all configuration values.
    """

    _instance: Optional['Config'] = None
    _config_data: Dict[str, Any] = {}

    def __new__(cls) -> 'Config':
        """Singleton pattern - only one config instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self) -> None:
        """Load configuration from YAML file."""
        config_path = Path(__file__).parent / "config.yaml"

        if not config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}\n"
                "Please ensure config.yaml exists in the pipeline directory."
            )

        with open(config_path) as f:
            self._config_data = yaml.safe_load(f)

        # Create attribute access for top-level sections
        for key, value in self._config_data.items():
            if isinstance(value, dict):
                setattr(self, key, ConfigSection(value))
            else:
                setattr(self, key, value)

    def reload(self) -> None:
        """Reload configuration from disk (useful for testing)."""
        self._load()

    def get_weights(self, asset_type: str) -> Dict[str, float]:
        """
        Get weight profile for an asset type.

        Args:
            asset_type: One of 'store-of-value', 'smart-contract', 'defi', 'infrastructure'

        Returns:
            Dict of dimension -> weight (0.0-1.0)
        """
        weights_data = self._config_data.get('weights', {})
        if asset_type in weights_data:
            return weights_data[asset_type]
        return weights_data.get('default', {
            'institutional': 0.30,
            'revenue': 0.20,
            'regulatory': 0.20,
            'supply': 0.20,
            'wyckoff': 0.10,
        })

    def get_all_weights(self) -> Dict[str, Dict[str, float]]:
        """Get all weight profiles for dashboard export."""
        return self._config_data.get('weights', {})

    def to_dict(self) -> dict:
        """Return the raw config dict."""
        return self._config_data

    def __repr__(self) -> str:
        return f"Config(sections={list(self._config_data.keys())})"


# Singleton instance for easy import
config = Config()


# Convenience exports for common values
def get_rsi_thresholds() -> dict:
    """Get all RSI thresholds as a dict."""
    return config.rsi.to_dict()


def get_composite_thresholds() -> dict:
    """Get all composite thresholds as a dict."""
    return config.composite.to_dict()


def get_promotion_thresholds() -> dict:
    """Get all promotion thresholds as a dict."""
    return config.promotion.to_dict()


def get_wyckoff_config() -> dict:
    """Get full Wyckoff configuration."""
    return config.wyckoff.to_dict()
