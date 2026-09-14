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
    """Return an environment variable, or explain what to do if it is absent."""
    value = os.environ.get(name)
    if not value:
        raise MissingConfig(
            f"{name} is not set. Copy .env.example to .env and fill it in "
            f"(see .env.example for where to find this value)."
        )
    return value


def get(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


# Paths. Raw data is the evidence trail — read from it, never write into it.
RAW_DIR = PROJECT_ROOT / get("DATA_RAW_DIR", "data/raw")
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Default lookback window (days) for the pre-introduction contribution analysis.
LOOKBACK_DAYS = int(get("LOOKBACK_DAYS", "90"))
