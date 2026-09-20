"""Configuration loaded from the environment.

Real values live in `.env` (gitignored). `.env.example` documents every variable.
Ask for a secret through `require()` so a missing credential fails immediately with
a useful message instead of surfacing later as an opaque connection error.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


class MissingConfig(RuntimeError):
    """A required environment variable is not set."""


def require(name: str) -> str:
    """Return a secret, or explain what to do if it is absent.

    Resolution order: environment (including .env) first, then the macOS Keychain.
    The environment wins so that CI and one-off overrides work without touching
    stored secrets.
    """
    value = os.environ.get(name)
    if not value:
        value = _from_keychain(name)
    if not value:
        raise MissingConfig(
            f"{name} is not set. Either store it in the Keychain:\n"
            f"    python -m tn_accountability.secrets set {name}\n"
            f"or copy .env.example to .env and fill it in."
        )
    return value


def _from_keychain(name: str):
    """Look a secret up in the macOS Keychain. Returns None anywhere else."""
    try:
        from .secrets import get as keychain_get
        return keychain_get(name)
    except Exception:
        return None


def get(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


# Paths. Raw data is the evidence trail — read from it, never write into it.
RAW_DIR = PROJECT_ROOT / get("DATA_RAW_DIR", "data/raw")
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Default lookback window (days) for the pre-introduction contribution analysis.
LOOKBACK_DAYS = int(get("LOOKBACK_DAYS", "90"))
