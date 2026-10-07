"""Immutable models for one explicit civil target and deterministic dynamic palaces."""

from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.birth import BirthInput
from app.models.calendar import EarthlyBranch, Ganzhi, SUPPORTED_GREGORIAN_START
from app.models.flow_year import FlowYearResult
from app.models.ziwei import (
    AuxiliaryStarName,
    MajorStarName,
    PalaceName,
    StarCategory,
    TRANSFORMATION_ORDER,
    TransformationType,
)


class FlowMonthTransformation(BaseModel):
    """One monthly transformation tag at its unchanged natal-star location."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    transformation_type: TransformationType
    star_name: MajorStarName | AuxiliaryStarName
    star_category: StarCategory
    natal_branch: EarthlyBranch
    natal_palace_name: PalaceName

    @model_validator(mode="after")
    def validate_category(self) -> Self:
        expected = StarCategory.MAJOR if isinstance(self.star_name, MajorStarName) else StarCategory.AUXILIARY
        if self.star_category is not expected:
            raise ValueError("star_category must match the Flow-Month target star model")
        return self


class FlowDayTransformation(BaseModel):
    """One daily transformation tag at its unchanged natal-star location."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    transformation_type: TransformationType
    star_name: MajorStarName | AuxiliaryStarName
    star_category: StarCategory
    natal_branch: EarthlyBranch
    natal_palace_name: PalaceName

    @model_validator(mode="after")
    def validate_category(self) -> Self:
        expected = StarCategory.MAJOR if isinstance(self.star_name, MajorStarName) else StarCategory.AUXILIARY
        if self.star_category is not expected:
            raise ValueError("star_category must match the Flow-Day target star model")
        return self


class FlowDateInput(BaseModel):
    """An explicitly entered Gregorian civil/standard target datetime."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    year: int = Field(ge=1583, le=9999, strict=True)
    month: int = Field(ge=1, le=12, strict=True)
    day: int = Field(ge=1, le=31, strict=True)
    hour: int = Field(ge=0, le=23, strict=True)
    minute: int = Field(ge=0, le=59, strict=True)

    @model_validator(mode="after")
    def validate_supported_gregorian_datetime(self) -> Self:
        try:
            target_date = date(self.year, self.month, self.day)
        except ValueError as exc:
            raise ValueError(f"invalid Gregorian target date: {exc}") from exc
        if target_date < SUPPORTED_GREGORIAN_START:
            raise ValueError("target date must be on or after 1582-10-15")
        return self

    @property
    def value(self) -> datetime:
        return datetime(self.year, self.month, self.day, self.hour, self.minute)


class FlowDateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    birth_input: BirthInput
    target_datetime: FlowDateInput


class FlowMonthPalace(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    flow_palace_name: PalaceName
    earthly_branch: EarthlyBranch
    natal_palace_name: PalaceName
    natal_palace_ganzhi: Ganzhi

    @model_validator(mode="after")
    def validate_host_branch(self) -> Self:
        if self.natal_palace_ganzhi.earthly_branch != self.earthly_branch:
            raise ValueError("Flow-Month natal host Ganzhi must use the host branch")
        return self


class FlowMonthResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    lunar_year: int = Field(ge=1, le=9999, strict=True)
    lunar_month: int = Field(ge=1, le=12, strict=True)
    is_leap_month: bool = Field(strict=True)
    effective_month: int = Field(ge=1, le=13, strict=True)
    month_ganzhi: Ganzhi
    flow_month_life_palace_branch: EarthlyBranch
    natal_host_palace_name: PalaceName
    natal_host_palace_ganzhi: Ganzhi
    palaces: tuple[FlowMonthPalace, ...] = Field(min_length=12, max_length=12)
    transformations: tuple[FlowMonthTransformation, ...] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        if self.effective_month != self.lunar_month + int(self.is_leap_month):
            raise ValueError("Flow-Month effective month must apply the whole-leap-month rule")
        if len({item.flow_palace_name for item in self.palaces}) != 12:
            raise ValueError("Flow-Month must contain every palace exactly once")
        if len({item.earthly_branch for item in self.palaces}) != 12:
            raise ValueError("Flow-Month must contain every branch exactly once")
        life = self.palaces[0]
        if life.flow_palace_name is not PalaceName.LIFE:
            raise ValueError("Flow-Month first palace must be Life Palace")
        if life.earthly_branch != self.flow_month_life_palace_branch:
            raise ValueError("Flow-Month Life Palace branch mismatch")
        if (
            life.natal_palace_name != self.natal_host_palace_name
            or life.natal_palace_ganzhi != self.natal_host_palace_ganzhi
        ):
            raise ValueError("Flow-Month natal host summary mismatch")
        from app.ziwei.transformations import transformation_targets

        if tuple(item.transformation_type for item in self.transformations) != TRANSFORMATION_ORDER:
            raise ValueError("Flow-Month transformations must be in canonical order")
        if tuple(item.star_name for item in self.transformations) != transformation_targets(
            self.month_ganzhi.heavenly_stem
        ):
            raise ValueError("Flow-Month transformation targets must match its month stem")
        if len({item.star_name for item in self.transformations}) != 4:
            raise ValueError("Flow-Month transformation target stars must be unique")
        natal_hosts = {item.earthly_branch: item.natal_palace_name for item in self.palaces}
        for item in self.transformations:
            if natal_hosts.get(item.natal_branch) != item.natal_palace_name:
                raise ValueError("Flow-Month transformation location must match natal host")
        return self


class FlowDayPalace(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    flow_palace_name: PalaceName
    earthly_branch: EarthlyBranch
    natal_palace_name: PalaceName
    natal_palace_ganzhi: Ganzhi

    @model_validator(mode="after")
    def validate_host_branch(self) -> Self:
        if self.natal_palace_ganzhi.earthly_branch != self.earthly_branch:
            raise ValueError("Flow-Day natal host Ganzhi must use the host branch")
        return self


class FlowDayResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target_lunar_year: int = Field(ge=1, le=9999, strict=True)
    target_lunar_month: int = Field(ge=1, le=12, strict=True)
    target_lunar_day: int = Field(ge=1, le=30, strict=True)
    target_is_leap_month: bool = Field(strict=True)
    day_ganzhi: Ganzhi
    flow_day_life_palace_branch: EarthlyBranch
    natal_host_palace_name: PalaceName
    natal_host_palace_ganzhi: Ganzhi
    palaces: tuple[FlowDayPalace, ...] = Field(min_length=12, max_length=12)
    transformations: tuple[FlowDayTransformation, ...] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        if len({item.flow_palace_name for item in self.palaces}) != 12:
            raise ValueError("Flow-Day must contain every palace exactly once")
        if len({item.earthly_branch for item in self.palaces}) != 12:
            raise ValueError("Flow-Day must contain every branch exactly once")
        life = self.palaces[0]
        if life.flow_palace_name is not PalaceName.LIFE:
            raise ValueError("Flow-Day first palace must be Life Palace")
        if life.earthly_branch != self.flow_day_life_palace_branch:
            raise ValueError("Flow-Day Life Palace branch mismatch")
        if (
            life.natal_palace_name != self.natal_host_palace_name
            or life.natal_palace_ganzhi != self.natal_host_palace_ganzhi
        ):
            raise ValueError("Flow-Day natal host summary mismatch")
        from app.ziwei.transformations import transformation_targets

        if tuple(item.transformation_type for item in self.transformations) != TRANSFORMATION_ORDER:
            raise ValueError("Flow-Day transformations must be in canonical order")
        if tuple(item.star_name for item in self.transformations) != transformation_targets(
            self.day_ganzhi.heavenly_stem
        ):
            raise ValueError("Flow-Day transformation targets must match its day stem")
        if len({item.star_name for item in self.transformations}) != 4:
            raise ValueError("Flow-Day transformation target stars must be unique")
        natal_hosts = {item.earthly_branch: item.natal_palace_name for item in self.palaces}
        for item in self.transformations:
            if natal_hosts.get(item.natal_branch) != item.natal_palace_name:
                raise ValueError("Flow-Day transformation location must match natal host")
        return self


class FlowDateResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target_solar_datetime: datetime
    target_lunar_year: int = Field(ge=1, le=9999, strict=True)
    target_lunar_month: int = Field(ge=1, le=12, strict=True)
    target_lunar_day: int = Field(ge=1, le=30, strict=True)
    target_is_leap_month: bool = Field(strict=True)
    target_effective_month: int = Field(ge=1, le=13, strict=True)
    flow_year: FlowYearResult
    flow_month: FlowMonthResult
    flow_day: FlowDayResult

    @model_validator(mode="after")
    def validate_layers_share_target(self) -> Self:
        if self.flow_year.target_lunar_year != self.target_lunar_year:
            raise ValueError("Flow-Year must use the target lunar year")
        if (
            self.flow_month.lunar_year,
            self.flow_month.lunar_month,
            self.flow_month.is_leap_month,
            self.flow_month.effective_month,
        ) != (
            self.target_lunar_year,
            self.target_lunar_month,
            self.target_is_leap_month,
            self.target_effective_month,
        ):
            raise ValueError("Flow-Month must use the target lunar month")
        if (
            self.flow_day.target_lunar_year,
            self.flow_day.target_lunar_month,
            self.flow_day.target_lunar_day,
            self.flow_day.target_is_leap_month,
        ) != (
            self.target_lunar_year,
            self.target_lunar_month,
            self.target_lunar_day,
            self.target_is_leap_month,
        ):
            raise ValueError("Flow-Day must use the target lunar date")
        return self
