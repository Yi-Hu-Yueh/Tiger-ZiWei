"""Phase 6A deterministic Major-Luck placement; no transformations or annual luck."""

from collections.abc import Sequence
from typing import Protocol

from app.models.birth import Gender
from app.models.calendar import EARTHLY_BRANCHES, EarthlyBranch, Ganzhi, HeavenlyStem
from app.models.major_luck import (
    MajorLuckDirection,
    MajorLuckPeriod,
    MajorLuckPeriodTransformations,
    MajorLuckResult,
    MajorLuckTransformation,
    YearYinYang,
)
from app.models.ziwei import (
    AuxiliaryStarPlacement,
    FiveElementsBureauResult,
    MajorStarPlacement,
    PalaceName,
    StarCategory,
    TRANSFORMATION_ORDER,
)
from app.ziwei.transformations import TransformationStarName, _locate_target, transformation_targets


YANG_STEMS = frozenset({"甲", "丙", "戊", "庚", "壬"})
YIN_STEMS = frozenset({"乙", "丁", "己", "辛", "癸"})


class NatalPalace(Protocol):
    palace_name: PalaceName
    palace_ganzhi: Ganzhi
    major_stars: tuple[MajorStarPlacement, ...]
    auxiliary_stars: tuple[AuxiliaryStarPlacement, ...]

    @property
    def earthly_branch(self) -> EarthlyBranch: ...

    @property
    def heavenly_stem(self) -> HeavenlyStem: ...


def classify_year_stem(stem: HeavenlyStem) -> YearYinYang:
    """Classify the already-authoritative primary birth-year stem."""

    if stem in YANG_STEMS:
        return YearYinYang.YANG
    if stem in YIN_STEMS:
        return YearYinYang.YIN
    raise ValueError("unsupported Heavenly Stem")


def determine_major_luck_direction(stem: HeavenlyStem, gender: Gender | str) -> MajorLuckDirection:
    """陽男陰女順行，陰男陽女逆行."""

    yinyang = classify_year_stem(stem)
    normalized_gender = Gender(gender)
    same = (yinyang is YearYinYang.YANG and normalized_gender is Gender.MALE) or (
        yinyang is YearYinYang.YIN and normalized_gender is Gender.FEMALE
    )
    return MajorLuckDirection.FORWARD if same else MajorLuckDirection.REVERSE


def nominal_age_range(bureau_number: int, period_index: int) -> tuple[int, int]:
    """Return one inclusive ten-year range, using traditional nominal ages."""

    if isinstance(bureau_number, bool) or bureau_number not in {2, 3, 4, 5, 6}:
        raise ValueError("bureau number must be one of 2, 3, 4, 5, 6")
    if isinstance(period_index, bool) or not isinstance(period_index, int) or not 1 <= period_index <= 12:
        raise ValueError("period index must be an integer from 1 through 12")
    start = bureau_number + 10 * (period_index - 1)
    return start, start + 9


def major_luck_transformation_targets(stem: HeavenlyStem) -> tuple[TransformationStarName, ...]:
    """Reuse the single Phase 2B authoritative stem-to-target mapping."""

    return transformation_targets(stem)


def calculate_major_luck(
    *,
    year_heavenly_stem: HeavenlyStem,
    gender: Gender,
    bureau: FiveElementsBureauResult,
    palaces: Sequence[NatalPalace],
) -> MajorLuckResult:
    """Place twelve Major-Luck ranges on existing natal palaces by branch."""

    host_by_branch = {palace.earthly_branch: palace for palace in palaces}
    if set(host_by_branch) != set(EARTHLY_BRANCHES) or len(palaces) != 12:
        raise ValueError("Major-Luck calculation requires all twelve natal palace branches")
    life_hosts = [palace for palace in palaces if palace.palace_name is PalaceName.LIFE]
    if len(life_hosts) != 1:
        raise ValueError("Major-Luck calculation requires exactly one Life Palace")

    direction = determine_major_luck_direction(year_heavenly_stem, gender)
    step = 1 if direction is MajorLuckDirection.FORWARD else -1
    life_index = EARTHLY_BRANCHES.index(life_hosts[0].earthly_branch)
    periods: list[MajorLuckPeriod] = []
    for index in range(1, 13):
        branch = EARTHLY_BRANCHES[(life_index + step * (index - 1)) % 12]
        host = host_by_branch[branch]
        start, end = nominal_age_range(bureau.bureau_number, index)
        periods.append(
            MajorLuckPeriod(
                index=index,
                start_nominal_age=start,
                end_nominal_age=end,
                earthly_branch=branch,
                palace_name=host.palace_name,
                heavenly_stem=host.heavenly_stem,
                palace_ganzhi=host.palace_ganzhi,
            )
        )

    existing_stars = [
        (star.name, star.earthly_branch, StarCategory.MAJOR)
        for palace in palaces for star in palace.major_stars
    ] + [
        (star.name, star.earthly_branch, StarCategory.AUXILIARY)
        for palace in palaces for star in palace.auxiliary_stars
    ]
    period_transformations: list[MajorLuckPeriodTransformations] = []
    for period in periods:
        records: list[MajorLuckTransformation] = []
        for transformation_type, target in zip(
            TRANSFORMATION_ORDER, major_luck_transformation_targets(period.heavenly_stem), strict=True,
        ):
            _, branch, category = _locate_target(target, existing_stars)
            target_palace = host_by_branch[branch]
            records.append(
                MajorLuckTransformation(
                    transformation_type=transformation_type,
                    star_name=target,
                    star_category=category,
                    earthly_branch=branch,
                    natal_palace_name=target_palace.palace_name,
                )
            )
        period_transformations.append(
            MajorLuckPeriodTransformations(
                major_luck_index=period.index,
                start_nominal_age=period.start_nominal_age,
                end_nominal_age=period.end_nominal_age,
                major_luck_heavenly_stem=period.heavenly_stem,
                major_luck_earthly_branch=period.earthly_branch,
                major_luck_palace_name=period.palace_name,
                transformations=tuple(records),
            )
        )

    return MajorLuckResult(
        bureau_name=bureau.bureau_name,
        bureau_number=bureau.bureau_number,
        year_heavenly_stem=year_heavenly_stem,
        year_yinyang=classify_year_stem(year_heavenly_stem),
        gender=gender,
        direction=direction,
        periods=tuple(periods),
        period_transformations=tuple(period_transformations),
    )
