"""Validated Gregorian/lunar hierarchical inputs for deterministic dynamic queries."""

from datetime import date
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.birth import BirthInput
from app.models.calendar import LunarDate
from app.models.flow_date import FlowDayResult, FlowMonthResult
from app.models.flow_year import FlowYearResult


class SolarFlowQueryInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: Literal["solar"] = "solar"
    year: int = Field(ge=1583, le=9999, strict=True)
    month: int = Field(ge=1, le=12, strict=True)
    day: int = Field(ge=1, le=31, strict=True)

    @model_validator(mode="after")
    def validate_gregorian_date(self) -> Self:
        try:
            date(self.year, self.month, self.day)
        except ValueError as exc:
            raise ValueError(f"invalid Gregorian query date: {exc}") from exc
        return self


class LunarFlowQueryInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: Literal["lunar"] = "lunar"
    year: int = Field(ge=1583, le=9999, strict=True)
    month: int | None = Field(default=None, ge=1, le=12, strict=True)
    day: int | None = Field(default=None, ge=1, le=30, strict=True)
    is_leap_month: bool = Field(default=False, strict=True)

    @model_validator(mode="after")
    def validate_hierarchy_and_lunar_month(self) -> Self:
        if self.day is not None and self.month is None:
            raise ValueError("lunar day requires lunar month")
        if self.is_leap_month and self.month is None:
            raise ValueError("lunar leap-month state requires lunar month")
        if self.month is not None:
            from app.calendar.lunar import to_solar

            # Day one is used only to validate month/leap-month existence.  It is
            # never used to calculate partial-query Ganzhi or dynamic results.
            to_solar(
                LunarDate(
                    year=self.year,
                    month=self.month,
                    day=self.day or 1,
                    is_leap_month=self.is_leap_month,
                )
            )
        return self


FlowQueryInput = Annotated[
    SolarFlowQueryInput | LunarFlowQueryInput,
    Field(discriminator="mode"),
]


class FlowQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    birth_input: BirthInput
    query: FlowQueryInput


class NormalizedFlowTarget(BaseModel):
    """One canonical lunar target shared by every deterministic flow layer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    input_mode: Literal["solar", "lunar"]
    original_solar_date: date | None = None
    original_lunar_year: int | None = Field(default=None, ge=1583, le=9999, strict=True)
    original_lunar_month: int | None = Field(default=None, ge=1, le=12, strict=True)
    original_lunar_day: int | None = Field(default=None, ge=1, le=30, strict=True)
    original_is_leap_month: bool | None = None
    converted_solar_date: date | None = None
    lunar_year: int = Field(ge=1583, le=9999, strict=True)
    lunar_month: int | None = Field(default=None, ge=1, le=12, strict=True)
    lunar_day: int | None = Field(default=None, ge=1, le=30, strict=True)
    is_leap_month: bool = Field(strict=True)
    effective_month: int | None = Field(default=None, ge=1, le=13, strict=True)

    @model_validator(mode="after")
    def validate_granularity(self) -> Self:
        if self.lunar_day is not None and self.lunar_month is None:
            raise ValueError("normalized lunar day requires lunar month")
        if self.lunar_month is None and (self.is_leap_month or self.effective_month is not None):
            raise ValueError("normalized leap/effective month requires lunar month")
        if self.lunar_month is not None:
            expected = self.lunar_month + int(self.is_leap_month)
            if self.effective_month != expected:
                raise ValueError("normalized effective month mismatch")
        return self


class FlowQueryResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    query_mode: Literal["solar", "lunar"]
    original_query: FlowQueryInput
    normalized_target: NormalizedFlowTarget
    flow_year: FlowYearResult
    flow_month: FlowMonthResult | None = None
    flow_day: FlowDayResult | None = None

    @model_validator(mode="after")
    def validate_layers(self) -> Self:
        target = self.normalized_target
        if self.query_mode != target.input_mode or self.original_query.mode != self.query_mode:
            raise ValueError("flow-query mode mismatch")
        if self.flow_year.target_lunar_year != target.lunar_year:
            raise ValueError("Flow-Year must use normalized lunar year")
        if (self.flow_month is None) != (target.lunar_month is None):
            raise ValueError("Flow-Month presence must match normalized lunar month")
        if (self.flow_day is None) != (target.lunar_day is None):
            raise ValueError("Flow-Day presence must match normalized lunar day")
        return self
