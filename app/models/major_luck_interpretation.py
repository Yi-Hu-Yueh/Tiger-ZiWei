"""Strict facts, request, and result models for one Major-Luck interpretation."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.basic_chart import BirthDataSnapshot
from app.models.birth import BirthInput, Gender
from app.models.calendar import EarthlyBranch, Ganzhi, LunarDate
from app.models.interpretation import LLMResponseMetadata, NonEmptyText
from app.models.major_luck import MajorLuckDirection, MajorLuckPeriod, MajorLuckTransformation
from app.models.ziwei import (
    AuxiliaryStarName,
    BirthYearTransformation,
    MajorStarName,
    PalaceName,
    TRANSFORMATION_ORDER,
    TransformationType,
)


class MajorLuckInterpretationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    birth_input: BirthInput
    major_luck_index: int = Field(ge=1, le=12, strict=True)


class MajorLuckNatalPalaceFacts(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    palace_name: PalaceName
    earthly_branch: EarthlyBranch
    palace_ganzhi: Ganzhi
    is_life_palace: bool = Field(strict=True)
    has_body_palace: bool = Field(strict=True)
    major_stars: tuple[MajorStarName, ...]
    auxiliary_stars: tuple[AuxiliaryStarName, ...]
    birth_year_transformations: tuple[BirthYearTransformation, ...]


class MajorLuckInterpretationFacts(BaseModel):
    """Only authoritative natal and one selected ten-year-period facts."""

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
    direction: MajorLuckDirection
    selected_major_luck: MajorLuckPeriod
    major_luck_transformations: tuple[MajorLuckTransformation, ...] = Field(
        min_length=4, max_length=4,
    )

    @model_validator(mode="after")
    def validate_facts(self) -> Self:
        if self.gender != self.birth_data.gender:
            raise ValueError("Major-Luck interpretation gender must match normalized birth data")
        if len({item.earthly_branch for item in self.palaces}) != 12:
            raise ValueError("Major-Luck interpretation facts require twelve unique natal branches")
        if len({item.palace_name for item in self.palaces}) != 12:
            raise ValueError("Major-Luck interpretation facts require twelve unique natal palaces")
        if tuple(item.transformation_type for item in self.major_luck_transformations) != TRANSFORMATION_ORDER:
            raise ValueError("selected Major-Luck transformations must be in canonical order")
        return self


class MajorLuckTransformationInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    transformation_type: TransformationType
    star_name: MajorStarName | AuxiliaryStarName
    natal_palace_name: PalaceName
    analysis: NonEmptyText


class MajorLuckInterpretationResult(LLMResponseMetadata):
    """Fact-locked anchors plus concise interpretation of one selected period."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    major_luck_index: int = Field(ge=1, le=12, strict=True)
    start_nominal_age: int = Field(ge=1, strict=True)
    end_nominal_age: int = Field(ge=1, strict=True)
    palace_name: PalaceName
    earthly_branch: EarthlyBranch
    palace_ganzhi: Ganzhi
    overview: NonEmptyText
    host_palace_analysis: NonEmptyText
    transformation_analysis: tuple[MajorLuckTransformationInterpretation, ...] = Field(
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
        if self.end_nominal_age != self.start_nominal_age + 9:
            raise ValueError("Major-Luck interpretation must cover one ten-year nominal-age range")
        if self.palace_ganzhi.earthly_branch != self.earthly_branch:
            raise ValueError("Major-Luck interpretation palace Ganzhi is inconsistent")
        if tuple(item.transformation_type for item in self.transformation_analysis) != TRANSFORMATION_ORDER:
            raise ValueError("transformation analysis must be in 化祿、化權、化科、化忌 order")
        return self
