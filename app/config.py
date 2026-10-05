"""Application configuration.

The NVIDIA API key is optional until LLM functionality is introduced in a
later phase.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """Environment-backed application settings."""

    nvidia_api_key: str | None = None


def get_settings() -> Settings:
    """Read optional settings from the process environment."""
    return Settings(nvidia_api_key=os.getenv("NVIDIA_API_KEY") or None)
