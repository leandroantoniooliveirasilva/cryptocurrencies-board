"""Stable paths from repo layout: ``src/pipeline`` package and git root."""

from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parent


def repo_root() -> Path:
    """Repository root (contains ``src/``, ``out/``, ``scripts/``, ``public/``)."""
    return _PKG_ROOT.parent.parent


def pipeline_root() -> Path:
    """Pipeline package dir (``assets.yaml``, ``config.yaml``, ``storage/``)."""
    return _PKG_ROOT
