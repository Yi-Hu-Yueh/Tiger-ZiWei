"""Strict facts, request, and result models for one Flow-Year interpretation."""

from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.basic_chart import BirthDataSnapshot
from app.models.birth import BirthInput, Gender
from app.models.calendar import EarthlyBranch, Ganzhi, LunarDate
from app.models.flow_year import FlowYearResult
from app.models.interpretation import LLMResponseMetadata, NonEmptyText
from app.models.major_luck import MajorLuckDirection, MajorLuckPeriod, MajorLuckTransformation
from app.models.major_luck_interpretation import MajorLuckNatalPalaceFacts
from app.models.ziwei import (
    AuxiliaryStarName,
    BirthYearTransformation,
    MajorStarName,
    PalaceName,
    TRANSFORMATION_ORDER,
    TransformationType,
)


class FlowYearInterpretationRequest(BaseModel):
    """A birth input plus exactly one explicit Chinese lunar year."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    birth_input: BirthInput
    target_year: int = Field(ge=1583, le=9999, strict=True)


class ActiveMajorLuckStatus(str, Enum):
    ACTIVE = "active"
    BEFORE_FIRST = "before_first_major_luck"
    AFTER_SUPPORTED = "after_supported_major_luck"


class ActiveMajorLuckInterpretationAnchor(BaseModel):
    """Fact-locked current ten-year background, including honest null states."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: ActiveMajorLuckStatus
    major_luck_index: int | None = Field(default=None, ge=1, le=12, strict=True)
    start_nominal_age: int | None = Field(default=None, ge=1, strict=True)
    end_nominal_age: int | None = Field(default=None, ge=1, strict=True)
    palace_name: PalaceName | None = None
    earthly_branch: EarthlyBranch | None = None
    palace_ganzhi: Ganzhi | None = None

    @model_validator(mode="after")
    def validate_status(self) -> Self:
        period_values = (
            self.major_luck_index,
            self.start_nominal_age,
            self.end_nominal_age,
            self.palace_name,
            self.earthly_branch,
            self.palace_ganzhi,
        )
        if self.status is ActiveMajorLuckStatus.ACTIVE:
            if any(value is None for value in period_values):
                raise ValueError("active Major-Luck anchor requires all period facts")
            if self.end_nominal_age != self.start_nominal_age + 9:  # type: ignore[operator]
                raise ValueError("active Major-Luck anchor must span ten nominal ages")
            if self.palace_ganzhi.earthly_branch != self.earthly_branch:  # type: ignore[union-attr]
                raise ValueError("active Major-Luck anchor Ganzhi and branch disagree")
        elif any(value is not None for value in period_values):
            raise ValueError("inactive Major-Luck anchor must use explicit null period facts")
        return self


class FlowYearNatalHostAnchor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    palace_name: PalaceName
    earthly_branch: EarthlyBranch
    palace_ganzhi: Ganzhi

    @model_validator(mode="after")
    def validate_branch(self) -> Self:
        if self.palace_ganzhi.earthly_branch != self.earthly_branch:
            raise ValueError("Flow-Year natal-host Ganzhi and branch disagree")
        return self


class FlowYearInterpretationFacts(BaseModel):
    """Authoritative natal, Major-Luck, and selected Flow-Year layers."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    birth_data: BirthDataSnapshot
    gender: Gender
    lunar_date: LunarDate
    year_ganzhi: Ganzhi
    month_ganzhi: Ganzhi
    day_ganzhi: Ganzhi
    hour_ganzhi: Ganzhi
    life_palace_branch: EarthlyBranch
    body_palace_branch: EarthlyBranch
    body_palace_name: PalaceName
    bureau_name: str = Field(min_length=3)
    bureau_number: int = Field(ge=2, le=6, strict=True)
    palaces: tuple[MajorLuckNatalPalaceFacts, ...] = Field(min_length=12, max_length=12)
    birth_year_transformations: tuple[BirthYearTransformation, ...] = Field(
        min_length=4, max_length=4,
    )
    major_luck_direction: MajorLuckDirection
    active_major_luck: MajorLuckPeriod | None
    active_major_luck_transformations: tuple[MajorLuckTransformation, ...]
    before_first_major_luck: bool = Field(strict=True)
    after_supported_major_luck: bool = Field(strict=True)
    flow_year: FlowYearResult

    @model_validator(mode="after")
    def validate_layers(self) -> Self:
        if self.gender != self.birth_data.gender:
            raise ValueError("Flow-Year interpretation gender must match normalized birth data")
        if len({item.earthly_branch for item in self.palaces}) != 12:
            raise ValueError("Flow-Year interpretation facts require twelve unique natal branches")
        if len({item.palace_name for item in self.palaces}) != 12:
            raise ValueError("Flow-Year interpretation facts require twelve unique natal palaces")
        if self.active_major_luck != self.flow_year.active_major_luck:
            raise ValueError("active Major-Luck must be reused from FlowYearResult")
        if self.before_first_major_luck != self.flow_year.before_first_major_luck:
            raise ValueError("before-first status must be reused from FlowYearResult")
        if self.after_supported_major_luck != self.flow_year.after_supported_major_luck:
            raise ValueError("after-supported status must be reused from FlowYearResult")
        if self.active_major_luck is None:
            if self.active_major_luck_transformations:
                raise ValueError("inactive Major-Luck cannot contain transformations")
        elif tuple(
            item.transformation_type for item in self.active_major_luck_transformations
        ) != TRANSFORMATION_ORDER:
            raise ValueError("active Major-Luck transformations must be in canonical order")
        return self


class FlowYearTransformationInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    transformation_type: TransformationType
    star_name: MajorStarName | AuxiliaryStarName
    natal_palace_name: PalaceName
    analysis: NonEmptyText


class FlowYearInterpretationResult(LLMResponseMetadata):
    """Fact-locked anchors plus restrained interpretation of one selected year."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    target_year: int = Field(ge=1583, le=9999, strict=True)
    flow_year_ganzhi: Ganzhi
    nominal_age: int = Field(ge=1, strict=True)
    flow_life_palace_branch: EarthlyBranch
    flow_life_palace_natal_host: FlowYearNatalHostAnchor
    active_major_luck_summary: ActiveMajorLuckInterpretationAnchor
    overview: NonEmptyText
    flow_life_palace_analysis: NonEmptyText
    major_luck_context: NonEmptyText
    transformation_analysis: tuple[FlowYearTransformationInterpretation, ...] = Field(
        min_length=4, max_length=4,
    )
    career: NonEmptyText
    finance: NonEmptyText
    relationships: NonEmptyText
    family_and_interpersonal: NonEmptyText
    strengths: NonEmptyText
    potential_challenges: NonEmptyText
    practical_focus: NonEmptyText

    @model_validator(mode="after")
    def validate_structure(self) -> Self:
        if self.flow_year_ganzhi.earthly_branch != self.flow_life_palace_branch:
            raise ValueError("Flow-Year Life Palace must equal the annual Earthly Branch")
        if self.flow_life_palace_natal_host.earthly_branch != self.flow_life_palace_branch:
            raise ValueError("Flow-Year natal host must be at the Life Palace branch")
        if tuple(item.transformation_type for item in self.transformation_analysis) != TRANSFORMATION_ORDER:
            raise ValueError("Flow-Year transformation analysis must be in canonical order")
        return self
