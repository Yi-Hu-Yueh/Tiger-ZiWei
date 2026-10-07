"""Deterministic public metadata for the selectable interpretation models."""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.llm.model_registry import enabled_models


router = APIRouter()


class PublicLLMModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    display_name: str
    default: bool


@router.get("/api/llm/models", response_model=tuple[PublicLLMModel, ...])
def list_llm_models() -> tuple[PublicLLMModel, ...]:
    return tuple(
        PublicLLMModel(id=model.id, display_name=model.display_name, default=model.default)
        for model in enabled_models()
    )
