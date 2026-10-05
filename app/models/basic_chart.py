"""Phase 1F composition models and authoritative upstream consistency checks."""

from datetime import date
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.models.birth import BirthData
from app.models.calendar import EARTHLY_BRANCHES, CalendarResult, EarthlyBranch, Ganzhi, HeavenlyStem, LunarDate
from app.models.ziwei import (
    FiveElementsBureauResult, MajorStarChart, MajorStarName, MajorStarPlacement,
    PalaceLayout, PalaceName,
    AuxiliaryStarChart, AuxiliaryStarPlacement, BirthYearTransformations,
)


class BirthDataSnapshot(BirthData):
    """Freeze a copy of the accepted input without changing Phase 1A's model."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class BasicChartPalace(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    palace_name: PalaceName
    palace_ganzhi: Ganzhi
    has_body_palace: bool = Field(strict=True)
    major_stars: tuple[MajorStarPlacement, ...]
    auxiliary_stars: tuple[AuxiliaryStarPlacement, ...]

    @computed_field
    @property
    def earthly_branch(self) -> EarthlyBranch:
        return self.palace_ganzhi.earthly_branch

    @computed_field
    @property
    def heavenly_stem(self) -> HeavenlyStem:
        return self.palace_ganzhi.heavenly_stem

    @computed_field
    @property
    def is_life_palace(self) -> bool:
        return self.palace_name is PalaceName.LIFE

    @model_validator(mode="after")
    def validate_star_branches(self) -> Self:
        if any(s.earthly_branch != self.earthly_branch for s in (*self.major_stars, *self.auxiliary_stars)):
            raise ValueError("every grouped star must share its palace branch")
        return self


class BasicChartResult(BaseModel):
    """Basic core, not a complete chart. Upstream receipts remain unchanged.

    Validation deliberately calls the existing authoritative B-E functions
    again: even deserialization must reject forged but structurally valid
    upstream values. No astrology formulas are duplicated in this model.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    birth_data: BirthDataSnapshot
    calendar: CalendarResult
    palace_layout: PalaceLayout
    five_elements_bureau: FiveElementsBureauResult
    major_star_chart: MajorStarChart
    auxiliary_star_chart: AuxiliaryStarChart
    birth_year_transformations: BirthYearTransformations
    palaces: tuple[BasicChartPalace, ...] = Field(min_length=12, max_length=12)

    @model_validator(mode="after")
    def validate_composition(self) -> Self:
        # Local imports avoid coupling upstream model definitions to orchestration.
        from app.calendar.ganzhi import calculate_calendar
        from app.ziwei.palace import calculate_palaces
        from app.ziwei.five_elements import calculate_five_elements_bureau, palace_heavenly_stems
        from app.ziwei.main_stars import calculate_major_stars
        from app.ziwei.auxiliary_stars import calculate_auxiliary_stars
        from app.ziwei.transformations import calculate_birth_year_transformations

        if self.calendar != calculate_calendar(self.birth_data):
            raise ValueError("Phase 1B calendar identity mismatch")
        if self.palace_layout != calculate_palaces(self.calendar):
            raise ValueError("Phase 1C Life/Body/palace identity mismatch")
        if self.five_elements_bureau != calculate_five_elements_bureau(self.calendar, self.palace_layout):
            raise ValueError("Phase 1D bureau identity mismatch")
        if self.major_star_chart != calculate_major_stars(self.calendar.lunar_date, self.five_elements_bureau):
            raise ValueError("Phase 1E major-star identity mismatch")
        if self.auxiliary_star_chart != calculate_auxiliary_stars(self.calendar):
            raise ValueError("Phase 2A auxiliary-star identity mismatch")
        expected_transformations = calculate_birth_year_transformations(
            self.calendar, self.palace_layout, self.major_star_chart, self.auxiliary_star_chart,
        )
        if self.birth_year_transformations != expected_transformations:
            raise ValueError("Phase 2B birth-year transformation identity mismatch")
        if tuple(p.earthly_branch for p in self.palaces) != EARTHLY_BRANCHES:
            raise ValueError("palaces must contain each canonical branch once in canonical order")
        if {p.palace_name for p in self.palaces} != set(PalaceName):
            raise ValueError("palaces must contain each canonical palace name exactly once")
        if sum(p.is_life_palace for p in self.palaces) != 1:
            raise ValueError("exactly one Life Palace is required")
        if sum(p.has_body_palace for p in self.palaces) != 1:
            raise ValueError("exactly one Body Palace marker is required")
        source_palaces = {p.earthly_branch: p for p in self.palace_layout.palaces}
        stems = palace_heavenly_stems(self.calendar.year_ganzhi.heavenly_stem)
        for palace in self.palaces:
            source = source_palaces[palace.earthly_branch]
            if (palace.palace_name, palace.has_body_palace) != (source.name, source.has_body_palace):
                raise ValueError("grouped palace name/Body marker differs from Phase 1C")
            if palace.heavenly_stem != stems[palace.earthly_branch]:
                raise ValueError("palace Heavenly Stem rotation differs from Phase 1D")
            if palace.is_life_palace and palace.palace_ganzhi != self.five_elements_bureau.life_palace_ganzhi:
                raise ValueError("Life Palace Ganzhi differs from Phase 1D")
        stars = [s for p in self.palaces for s in p.major_stars]
        if len(stars) != 14 or {s.name for s in stars} != set(MajorStarName):
            raise ValueError("grouped palaces must contain fourteen distinct required major stars")
        if {s.name: s.earthly_branch for s in stars} != self.major_star_chart.star_to_branch:
            raise ValueError("grouped star placements differ from Phase 1E")
        auxiliary = [s for p in self.palaces for s in p.auxiliary_stars]
        expected = self.auxiliary_star_chart.star_to_branch
        if len(auxiliary) != len(expected) or {s.name: s.earthly_branch for s in auxiliary} != expected:
            raise ValueError("grouped auxiliary placements differ from Phase 2A")
        return self

    # Convenience accessors keep the upstream objects authoritative instead of
    # storing a second, potentially contradictory copy of each calendar value.
    @property
    def solar_date(self) -> date:
        return self.calendar.solar_date

    @property
    def lunar_date(self) -> LunarDate:
        return self.calendar.lunar_date

    @property
    def year_ganzhi(self) -> Ganzhi:
        return self.calendar.year_ganzhi

    @property
    def month_ganzhi(self) -> Ganzhi:
        return self.calendar.month_ganzhi

    @property
    def day_ganzhi(self) -> Ganzhi:
        return self.calendar.day_ganzhi

    @property
    def hour_ganzhi(self) -> Ganzhi:
        return self.calendar.hour_ganzhi

    @computed_field
    @property
    def life_palace_branch(self) -> EarthlyBranch:
        return self.palace_layout.life_palace_branch

    @computed_field
    @property
    def body_palace_branch(self) -> EarthlyBranch:
        return self.palace_layout.body_palace_branch

    @computed_field
    @property
    def body_palace_name(self) -> PalaceName:
        return self.palace_layout.body_palace_name
