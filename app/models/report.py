"""Validated inputs for deterministic dynamic Word report generation."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.birth import BirthInput
from app.models.flow_date import FlowDateInput
from app.models.flow_query import FlowQueryInput
from app.models.flow_year_interpretation import FlowYearInterpretationResult
from app.models.flow_period_interpretation import (
    FlowDayInterpretationResult,
    FlowMonthInterpretationResult,
)
from app.models.interpretation import InterpretationResult
from app.models.major_luck_interpretation import MajorLuckInterpretationResult


class MajorLuckReportInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    major_luck_index: int = Field(ge=1, le=12, strict=True)
    interpretation: MajorLuckInterpretationResult


class ReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    birth_input: BirthInput
    interpretation: InterpretationResult
    major_luck_report: MajorLuckReportInput | None = None
    target_flow_year: int | None = Field(default=None, ge=1583, le=9999, strict=True)
    target_datetime: FlowDateInput | None = None
    flow_query: FlowQueryInput | None = None
    flow_year_interpretation: FlowYearInterpretationResult | None = None
    flow_month_interpretation: FlowMonthInterpretationResult | None = None
    flow_day_interpretation: FlowDayInterpretationResult | None = None

    @model_validator(mode="after")
    def validate_flow_year_state(self) -> Self:
        targets = (self.target_flow_year, self.target_datetime, self.flow_query)
        if sum(target is not None for target in targets) > 1:
            raise ValueError("use only one Flow-Year, Flow-Date, or Flow-Query target")
        if self.flow_year_interpretation is not None:
            if all(target is None for target in targets):
                raise ValueError("Flow-Year interpretation requires a calculated target Flow-Year")
            if (
                self.target_flow_year is not None
                and self.flow_year_interpretation.target_year != self.target_flow_year
            ):
                raise ValueError("Flow-Year interpretation must match the calculated target Flow-Year")
        if self.flow_month_interpretation is not None and self.flow_query is None:
            raise ValueError("Flow-Month interpretation requires a Flow-Query target")
        if self.flow_day_interpretation is not None and self.flow_query is None:
            raise ValueError("Flow-Day interpretation requires a Flow-Query target")
        return self
