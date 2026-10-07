"""Request-scoped NVIDIA model and credential selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Header, HTTPException

from app.llm.model_registry import LLMModelConfig, get_model_config
from app.llm.nvidia_client import NvidiaClient


@dataclass(frozen=True, slots=True)
class LLMRequestSelection:
    model: LLMModelConfig
    api_key: str | None

    def client(self, *, timeout: float) -> NvidiaClient:
        return NvidiaClient(api_key=self.api_key, model_id=self.model.id, timeout=timeout)

    def configure_interpreter(self, interpreter, *, timeout: float):
        """Replace the constructor default before any provider call is made."""

        interpreter._client = self.client(timeout=timeout)
        return interpreter


def resolve_llm_request_selection(
    api_key: Annotated[
        str | None,
        Header(alias="X-Tiger-NVIDIA-API-Key", include_in_schema=False),
    ] = None,
    model_id: Annotated[
        str | None,
        Header(alias="X-Tiger-NVIDIA-Model"),
    ] = None,
) -> LLMRequestSelection:
    try:
        model = get_model_config(model_id)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail={"code": "UNSUPPORTED_LLM_MODEL", "message": "不支援指定的 NVIDIA 模型。"},
        ) from None
    request_key = api_key.strip() if api_key and api_key.strip() else None
    return LLMRequestSelection(model=model, api_key=request_key)


def attach_llm_metadata(result, selection: LLMRequestSelection):
    """Attach trusted metadata after the LLM response has passed validation."""

    return result.model_copy(
        update={
            "provider": selection.model.provider,
            "model": selection.model.id,
            "model_display_name": selection.model.display_name,
        }
    )

