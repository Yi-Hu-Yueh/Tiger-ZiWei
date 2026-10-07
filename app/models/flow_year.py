"""Immutable request and result models for the deterministic Flow-Year core."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.birth import BirthInput
from app.models.calendar import EarthlyBranch, Ganzhi, HeavenlyStem
from app.models.major_luck import MajorLuckPeriod
from app.models.ziwei import (
    AuxiliaryStarName,
    MajorStarName,
    PalaceName,
    StarCategory,
    TRANSFORMATION_ORDER,
    TransformationType,
)


class FlowYearRequest(BaseModel):
    """One chart input and one explicitly supplied Chinese lunar year."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    birth_input: BirthInput
    target_year: int = Field(ge=1583, le=9999, strict=True)


class FlowYearPalace(BaseModel):
    """One annual palace name resolved onto an unchanged natal palace."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    flow_palace_name: PalaceName
    earthly_branch: EarthlyBranch
    natal_palace_name: PalaceName
    natal_palace_heavenly_stem: HeavenlyStem
    natal_palace_ganzhi: Ganzhi

    @model_validator(mode="after")
    def validate_natal_host(self) -> Self:
        if (
            self.natal_palace_ganzhi.heavenly_stem != self.natal_palace_heavenly_stem
            or self.natal_palace_ganzhi.earthly_branch != self.earthly_branch
        ):
            raise ValueError("Flow-Year host facts must reuse one natal palace Ganzhi")
        return self


class FlowYearTransformation(BaseModel):
    """One annual transformation tag at its unchanged natal-star location."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    transformation_type: TransformationType
    star_name: MajorStarName | AuxiliaryStarName
    star_category: StarCategory
    earthly_branch: EarthlyBranch
    natal_palace_name: PalaceName

    @model_validator(mode="after")
    def validate_category(self) -> Self:
        expected = (
            StarCategory.MAJOR if isinstance(self.star_name, MajorStarName)
            else StarCategory.AUXILIARY
        )
        if self.star_category is not expected:
            raise ValueError("star_category must match the Flow-Year target star model")
        return self


class FlowYearResult(BaseModel):
    """A complete annual palace rotation plus explicit Major-Luck lookup."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    target_lunar_year: int = Field(ge=1583, le=9999, strict=True)
    heavenly_stem: HeavenlyStem
    earthly_branch: EarthlyBranch
    ganzhi: Ganzhi
    nominal_age: int = Field(ge=1, strict=True)
    flow_life_palace_branch: EarthlyBranch
    palaces: tuple[FlowYearPalace, ...] = Field(min_length=12, max_length=12)
    transformations: tuple[FlowYearTransformation, ...] = Field(min_length=4, max_length=4)
    active_major_luck: MajorLuckPeriod | None
    before_first_major_luck: bool = Field(strict=True)
    after_supported_major_luck: bool = Field(strict=True)

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        from app.calendar.ganzhi import calculate_lunar_year_ganzhi
        from app.ziwei.flow_year import FLOW_YEAR_PALACE_ORDER, flow_year_palace_branches

        if self.ganzhi != calculate_lunar_year_ganzhi(self.target_lunar_year):
            raise ValueError("Flow-Year Ganzhi must match the authoritative target lunar year")
        if (
            self.ganzhi.heavenly_stem != self.heavenly_stem
            or self.ganzhi.earthly_branch != self.earthly_branch
        ):
            raise ValueError("Flow-Year stem and branch must match its Ganzhi")
        if self.flow_life_palace_branch != self.earthly_branch:
            raise ValueError("Flow-Year Life Palace branch must equal the annual branch")
        if tuple(item.flow_palace_name for item in self.palaces) != FLOW_YEAR_PALACE_ORDER:
            raise ValueError("Flow-Year palaces must follow the canonical annual order")
        expected_branches = flow_year_palace_branches(self.flow_life_palace_branch)
        if tuple(item.earthly_branch for item in self.palaces) != expected_branches:
            raise ValueError("Flow-Year palace branches must rotate forward from annual Life Palace")
        if len({item.earthly_branch for item in self.palaces}) != 12:
            raise ValueError("Flow-Year palaces must contain twelve unique branches")

        from app.ziwei.transformations import transformation_targets

        if tuple(item.transformation_type for item in self.transformations) != TRANSFORMATION_ORDER:
            raise ValueError("Flow-Year transformations must be in 化祿、化權、化科、化忌 order")
        if tuple(item.star_name for item in self.transformations) != transformation_targets(
            self.heavenly_stem
        ):
            raise ValueError("Flow-Year transformation targets must match its annual stem")
        if len({item.star_name for item in self.transformations}) != 4:
            raise ValueError("Flow-Year transformation target stars must be unique")
        natal_hosts = {item.earthly_branch: item.natal_palace_name for item in self.palaces}
        for item in self.transformations:
            if natal_hosts.get(item.earthly_branch) != item.natal_palace_name:
                raise ValueError("Flow-Year transformation location must match its natal host palace")

        inactive_flags = int(self.before_first_major_luck) + int(self.after_supported_major_luck)
        if self.active_major_luck is None:
            if inactive_flags != 1:
                raise ValueError("an inactive Major-Luck lookup must identify before or after range")
        else:
            if inactive_flags:
                raise ValueError("an active Major-Luck period cannot have an out-of-range flag")
            if not (
                self.active_major_luck.start_nominal_age
                <= self.nominal_age
                <= self.active_major_luck.end_nominal_age
            ):
                raise ValueError("active Major-Luck period must contain the nominal age")
        return self
