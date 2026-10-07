"""Strict facts and fact-locked results for Flow-Month and Flow-Day interpretation."""

import re
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.birth import BirthInput
from app.models.calendar import EarthlyBranch, Ganzhi
from app.models.flow_date import FlowDayResult, FlowMonthResult
from app.models.flow_query import FlowQueryInput
from app.models.flow_year_interpretation import FlowYearInterpretationFacts
from app.models.interpretation import LLMResponseMetadata, NonEmptyText
from app.models.ziwei import (
    AuxiliaryStarName,
    MajorStarName,
    PalaceName,
    TRANSFORMATION_ORDER,
    TransformationType,
)


class FlowMonthInterpretationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    birth_input: BirthInput
    query: FlowQueryInput


class FlowDayInterpretationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    birth_input: BirthInput
    query: FlowQueryInput


class FlowMonthInterpretationFacts(BaseModel):
    """Complete natal/Major-Luck/Flow-Year context plus exactly one Flow-Month."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    flow_year_facts: FlowYearInterpretationFacts
    flow_month: FlowMonthResult

    @model_validator(mode="after")
    def validate_layers(self) -> Self:
        year = self.flow_year_facts.flow_year
        month = self.flow_month
        if year.target_lunar_year != month.lunar_year:
            raise ValueError("Flow-Month interpretation layers must share the lunar year")
        return self


class FlowDayInterpretationFacts(BaseModel):
    """Complete natal through Flow-Day facts with every layer kept separate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    flow_year_facts: FlowYearInterpretationFacts
    flow_month: FlowMonthResult
    flow_day: FlowDayResult

    @model_validator(mode="after")
    def validate_layers(self) -> Self:
        year = self.flow_year_facts.flow_year
        month = self.flow_month
        day = self.flow_day
        if year.target_lunar_year != month.lunar_year or (
            day.target_lunar_year,
            day.target_lunar_month,
            day.target_is_leap_month,
        ) != (
            month.lunar_year,
            month.lunar_month,
            month.is_leap_month,
        ):
            raise ValueError("Flow-Day interpretation layers must share one lunar target")
        return self


class FlowPeriodTransformationInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    transformation_type: TransformationType
    star_name: MajorStarName | AuxiliaryStarName
    natal_palace_name: PalaceName
    analysis: NonEmptyText


_FORBIDDEN_PROPHECY = ("一定", "必然", "肯定發生", "必定")
_UNSUPPORTED_ASTROLOGY = ("流時", "小限", "童限", "廟旺陷", "長生十二神", "命主", "身主")


def _analysis_texts(model: BaseModel) -> tuple[str, ...]:
    def collect(value) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            return [text for item in value.values() for text in collect(item)]
        if isinstance(value, (list, tuple)):
            return [text for item in value for text in collect(item)]
        return []

    payload = model.model_dump(mode="python")
    for field in (
        "lunar_year", "lunar_month", "lunar_day", "is_leap_month", "month_ganzhi",
        "day_ganzhi", "flow_month_life_palace_branch", "flow_day_life_palace_branch",
        "natal_host_palace",
    ):
        payload.pop(field, None)
    return tuple(collect(payload))


def _validate_interpretation_language(model: BaseModel, *, day_level: bool) -> None:
    texts = _analysis_texts(model)
    forbidden = _FORBIDDEN_PROPHECY + _UNSUPPORTED_ASTROLOGY
    if any(term in text for text in texts for term in forbidden):
        raise ValueError("interpretation contains deterministic or unsupported astrology claims")
    if day_level and any(
        re.search(r"(?:上午|下午|晚間|晚上|凌晨|子時|丑時|寅時|卯時|辰時|巳時|午時|未時|申時|酉時|戌時|亥時|\d{1,2}\s*[點時])", text)
        for text in texts
    ):
        raise ValueError("Flow-Day interpretation cannot contain exact-hour claims")


class FlowMonthInterpretationResult(LLMResponseMetadata):
    model_config = ConfigDict(extra="forbid", frozen=True)

    lunar_year: int = Field(ge=1583, le=9999, strict=True)
    lunar_month: int = Field(ge=1, le=12, strict=True)
    is_leap_month: bool = Field(strict=True)
    month_ganzhi: Ganzhi
    flow_month_life_palace_branch: EarthlyBranch
    natal_host_palace: PalaceName
    overview: NonEmptyText
    life_palace_analysis: NonEmptyText
    major_luck_context: NonEmptyText
    flow_year_context: NonEmptyText
    transformation_analysis: tuple[FlowPeriodTransformationInterpretation, ...] = Field(
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
        if tuple(item.transformation_type for item in self.transformation_analysis) != TRANSFORMATION_ORDER:
            raise ValueError("Flow-Month transformation analysis must be in canonical order")
        _validate_interpretation_language(self, day_level=False)
        return self


class FlowDayInterpretationResult(LLMResponseMetadata):
    model_config = ConfigDict(extra="forbid", frozen=True)

    lunar_year: int = Field(ge=1583, le=9999, strict=True)
    lunar_month: int = Field(ge=1, le=12, strict=True)
    lunar_day: int = Field(ge=1, le=30, strict=True)
    is_leap_month: bool = Field(strict=True)
    day_ganzhi: Ganzhi
    flow_day_life_palace_branch: EarthlyBranch
    natal_host_palace: PalaceName
    overview: NonEmptyText
    life_palace_analysis: NonEmptyText
    major_luck_context: NonEmptyText
    flow_year_context: NonEmptyText
    flow_month_context: NonEmptyText
    transformation_analysis: tuple[FlowPeriodTransformationInterpretation, ...] = Field(
        min_length=4, max_length=4,
    )
    work: NonEmptyText
    finance: NonEmptyText
    relationships: NonEmptyText
    family_and_interpersonal: NonEmptyText
    strengths: NonEmptyText
    potential_challenges: NonEmptyText
    practical_focus: NonEmptyText

    @model_validator(mode="after")
    def validate_structure(self) -> Self:
        if tuple(item.transformation_type for item in self.transformation_analysis) != TRANSFORMATION_ORDER:
            raise ValueError("Flow-Day transformation analysis must be in canonical order")
        _validate_interpretation_language(self, day_level=True)
        return self
