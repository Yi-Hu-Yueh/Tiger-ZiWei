"""Explicit immutable models for the Phase 6A Major-Luck result."""

from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.birth import Gender
from app.models.calendar import EARTHLY_BRANCHES, EarthlyBranch, Ganzhi, HeavenlyStem
from app.models.ziwei import (
    AuxiliaryStarName,
    MajorStarName,
    PalaceName,
    StarCategory,
    TRANSFORMATION_ORDER,
    TransformationType,
)


class YearYinYang(str, Enum):
    YANG = "陽"
    YIN = "陰"


class MajorLuckDirection(str, Enum):
    FORWARD = "順行"
    REVERSE = "逆行"


class MajorLuckTransformation(BaseModel):
    """One Major-Luck tag resolved to an unchanged natal-star location."""

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
            raise ValueError("star_category must match the Major-Luck target star model")
        return self


class MajorLuckPeriodTransformations(BaseModel):
    """The four stem-selected transformations attached to one verified period."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    major_luck_index: int = Field(ge=1, le=12, strict=True)
    start_nominal_age: int = Field(ge=1, strict=True)
    end_nominal_age: int = Field(ge=1, strict=True)
    major_luck_heavenly_stem: HeavenlyStem
    major_luck_earthly_branch: EarthlyBranch
    major_luck_palace_name: PalaceName
    transformations: tuple[MajorLuckTransformation, ...] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def validate_period_transformations(self) -> Self:
        from app.ziwei.transformations import transformation_targets

        if self.end_nominal_age != self.start_nominal_age + 9:
            raise ValueError("Major-Luck transformation metadata must span ten nominal ages")
        if tuple(row.transformation_type for row in self.transformations) != TRANSFORMATION_ORDER:
            raise ValueError("Major-Luck transformations must be in 化祿、化權、化科、化忌 order")
        if tuple(row.star_name for row in self.transformations) != transformation_targets(
            self.major_luck_heavenly_stem
        ):
            raise ValueError("Major-Luck transformation targets must match the shared ten-stem table")
        if len({row.star_name for row in self.transformations}) != 4:
            raise ValueError("Major-Luck transformation target stars must be unique within a period")
        return self


class MajorLuckPeriod(BaseModel):
    """One ten-year nominal-age range hosted by one natal palace."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    index: int = Field(ge=1, le=12, strict=True)
    start_nominal_age: int = Field(ge=1, strict=True)
    end_nominal_age: int = Field(ge=1, strict=True)
    earthly_branch: EarthlyBranch
    palace_name: PalaceName
    heavenly_stem: HeavenlyStem
    palace_ganzhi: Ganzhi

    @model_validator(mode="after")
    def validate_period(self) -> Self:
        if self.end_nominal_age != self.start_nominal_age + 9:
            raise ValueError("a Major-Luck period must span exactly ten nominal ages")
        if (
            self.palace_ganzhi.heavenly_stem != self.heavenly_stem
            or self.palace_ganzhi.earthly_branch != self.earthly_branch
        ):
            raise ValueError("Major-Luck palace Ganzhi must be the host natal palace Ganzhi")
        return self


class MajorLuckResult(BaseModel):
    """All twelve deterministic natal-chart Major-Luck ranges."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    bureau_name: str = Field(min_length=3)
    bureau_number: int = Field(ge=2, le=6, strict=True)
    year_heavenly_stem: HeavenlyStem
    year_yinyang: YearYinYang
    gender: Gender
    direction: MajorLuckDirection
    periods: tuple[MajorLuckPeriod, ...] = Field(min_length=12, max_length=12)
    period_transformations: tuple[MajorLuckPeriodTransformations, ...] = Field(
        min_length=12, max_length=12,
    )

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        from app.ziwei.major_luck import classify_year_stem, determine_major_luck_direction

        bureau_names = {2: "水二局", 3: "木三局", 4: "金四局", 5: "土五局", 6: "火六局"}
        if self.bureau_name != bureau_names.get(self.bureau_number):
            raise ValueError("Major-Luck bureau name and number disagree")
        if self.year_yinyang is not classify_year_stem(self.year_heavenly_stem):
            raise ValueError("Major-Luck year yin/yang differs from the primary year stem")
        if self.direction is not determine_major_luck_direction(self.year_heavenly_stem, self.gender):
            raise ValueError("Major-Luck direction differs from year-stem yin/yang and gender")
        if tuple(period.index for period in self.periods) != tuple(range(1, 13)):
            raise ValueError("Major-Luck periods must be indexed 1 through 12")
        expected_starts = tuple(self.bureau_number + 10 * index for index in range(12))
        if tuple(period.start_nominal_age for period in self.periods) != expected_starts:
            raise ValueError("Major-Luck nominal-age ranges must start from the bureau number without gaps")
        if len({period.earthly_branch for period in self.periods}) != 12:
            raise ValueError("Major-Luck periods must contain twelve unique Earthly Branches")
        start_index = EARTHLY_BRANCHES.index(self.periods[0].earthly_branch)
        step = 1 if self.direction is MajorLuckDirection.FORWARD else -1
        expected_branches = tuple(EARTHLY_BRANCHES[(start_index + step * i) % 12] for i in range(12))
        if tuple(period.earthly_branch for period in self.periods) != expected_branches:
            raise ValueError("Major-Luck periods must follow canonical Earthly-Branch direction")
        if tuple(item.major_luck_index for item in self.period_transformations) != tuple(range(1, 13)):
            raise ValueError("Major-Luck transformation groups must be indexed 1 through 12")
        for period, group in zip(self.periods, self.period_transformations, strict=True):
            if (
                group.major_luck_index != period.index
                or group.start_nominal_age != period.start_nominal_age
                or group.end_nominal_age != period.end_nominal_age
                or group.major_luck_heavenly_stem != period.heavenly_stem
                or group.major_luck_earthly_branch != period.earthly_branch
                or group.major_luck_palace_name is not period.palace_name
            ):
                raise ValueError("Major-Luck transformation metadata must match its verified period")
        if sum(len(item.transformations) for item in self.period_transformations) != 48:
            raise ValueError("Major-Luck result must contain exactly 48 transformation records")
        return self

    def find_by_nominal_age(self, age: int) -> MajorLuckPeriod | None:
        """Return the range containing an explicitly supplied nominal age."""

        if isinstance(age, bool) or not isinstance(age, int):
            raise ValueError("nominal age must be an integer")
        return next(
            (period for period in self.periods if period.start_nominal_age <= age <= period.end_nominal_age),
            None,
        )
