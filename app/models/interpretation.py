"""Validated structured output for restrained Zi Wei interpretation."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from app.models.ziwei import PalaceName


NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class PalaceInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    palace_name: PalaceName
    summary: NonEmptyText


class OverallInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    personality: NonEmptyText
    career: NonEmptyText
    finance: NonEmptyText
    relationships: NonEmptyText
    interpersonal: NonEmptyText
    family: NonEmptyText
    strengths: NonEmptyText
    potential_challenges: NonEmptyText


class LLMResponseMetadata(BaseModel):
    """Trusted backend metadata; it is never part of the LLM output prompt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: Literal["NVIDIA"] | None = None
    model: NonEmptyText | None = None
    model_display_name: NonEmptyText | None = None

    @model_validator(mode="after")
    def require_complete_metadata(self) -> Self:
        values = (self.provider, self.model, self.model_display_name)
        if any(value is not None for value in values) and any(value is None for value in values):
            raise ValueError("LLM response metadata must be complete")
        return self


class InterpretationResult(LLMResponseMetadata):
    model_config = ConfigDict(extra="forbid", frozen=True)

    overview: NonEmptyText
    palace_interpretations: tuple[PalaceInterpretation, ...]
    transformation_analysis: NonEmptyText
    overall: OverallInterpretation

    @model_validator(mode="after")
    def require_exactly_one_analysis_per_palace(self) -> Self:
        names = tuple(item.palace_name for item in self.palace_interpretations)
        expected = set(PalaceName)
        if len(names) != 12 or len(set(names)) != 12 or set(names) != expected:
            raise ValueError("palace_interpretations must contain each canonical palace exactly once")
        return self
