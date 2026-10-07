"""Single safe registry for selectable NVIDIA-hosted interpretation models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LLMModelConfig:
    id: str
    display_name: str
    provider: str
    reasoning_effort: str
    supports_clear_thinking: bool
    clear_thinking_value: bool | None
    enabled: bool
    default: bool = False


MODEL_REGISTRY: tuple[LLMModelConfig, ...] = (
    LLMModelConfig(
        id="z-ai/glm-5.3-flash",
        display_name="GLM-5.3-Flash",
        provider="NVIDIA",
        reasoning_effort="low",
        supports_clear_thinking=True,
        clear_thinking_value=True,
        enabled=True,
        default=True,
    ),
    LLMModelConfig(
        id="openai/gpt-oss-20b",
        display_name="GPT-OSS-20B",
        provider="NVIDIA",
        reasoning_effort="low",
        supports_clear_thinking=False,
        clear_thinking_value=None,
        enabled=True,
    ),
)


def enabled_models() -> tuple[LLMModelConfig, ...]:
    return tuple(model for model in MODEL_REGISTRY if model.enabled)


def default_model() -> LLMModelConfig:
    return next(model for model in enabled_models() if model.default)


def get_model_config(model_id: str | None = None) -> LLMModelConfig:
    """Resolve an enabled model, defaulting only when no id was supplied."""

    if model_id is None or not model_id.strip():
        return default_model()
    normalized = model_id.strip()
    for model in enabled_models():
        if model.id == normalized:
            return model
    raise ValueError("unsupported NVIDIA model")

