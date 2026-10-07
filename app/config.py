"""Small, fixed configuration surface for Tiger-ZiWei."""

import os
from dataclasses import dataclass
from pathlib import Path


NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODEL = "z-ai/glm-5.3-flash"
NVIDIA_REASONING_EFFORT = "low"
NVIDIA_CLEAR_THINKING = True
PROJECT_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


@dataclass(frozen=True, slots=True)
class Settings:
    """Environment-backed application settings."""

    nvidia_api_key: str | None = None
    nvidia_api_url: str = NVIDIA_API_URL
    nvidia_model: str = NVIDIA_MODEL
    nvidia_reasoning_effort: str = NVIDIA_REASONING_EFFORT
    nvidia_clear_thinking: bool = NVIDIA_CLEAR_THINKING


def _project_env_api_key() -> tuple[bool, str | None]:
    """Read only NVIDIA_API_KEY from the project-local .env, if present."""

    try:
        lines = PROJECT_ENV_PATH.read_text(encoding="utf-8-sig").splitlines()
    except (FileNotFoundError, OSError, UnicodeError):
        return False, None
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() != "NVIDIA_API_KEY":
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1].strip()
        return True, value or None
    return False, None


def get_settings() -> Settings:
    """Read the secret with project .env precedence over process environment."""

    project_key_is_defined, project_key = _project_env_api_key()
    api_key = project_key if project_key_is_defined else os.getenv("NVIDIA_API_KEY")
    return Settings(nvidia_api_key=api_key.strip() if api_key and api_key.strip() else None)
