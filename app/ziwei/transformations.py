"""Deterministic birth-year Four Transformations; placement/tagging only.

The table follows Tiger-ZiWei's documented 《紫微斗數全書》 edition choice.
It selects four existing star names from the primary Phase 1B year stem and
never derives a year, creates a star, moves a star, or interprets a result.
"""

from types import MappingProxyType

from app.models.calendar import CalendarResult, HeavenlyStem
from app.models.ziwei import (
    AuxiliaryStarChart,
    AuxiliaryStarName,
    BirthYearTransformation,
    BirthYearTransformations,
    MajorStarChart,
    MajorStarName,
    PalaceLayout,
    StarCategory,
    TRANSFORMATION_ORDER,
)


TransformationStarName = MajorStarName | AuxiliaryStarName


# Canonical order in every row: 化祿、化權、化科、化忌.
# 壬 uses 天府 per the primary 南陽堂《紫微斗數全書》 edition. The older
# 《紫微斗數捷覽》/《紫微斗數全集》 左輔 reading is an edition variant.
BIRTH_YEAR_TRANSFORMATION_TARGETS = MappingProxyType({
    "甲": (MajorStarName.LIANZHEN, MajorStarName.POJUN,
          MajorStarName.WUQU, MajorStarName.TAIYANG),
    "乙": (MajorStarName.TIANJI, MajorStarName.TIANLIANG,
          MajorStarName.ZIWEI, MajorStarName.TAIYIN),
    "丙": (MajorStarName.TIANTONG, MajorStarName.TIANJI,
          AuxiliaryStarName.WENCHANG, MajorStarName.LIANZHEN),
    "丁": (MajorStarName.TAIYIN, MajorStarName.TIANTONG,
          MajorStarName.TIANJI, MajorStarName.JUMEN),
    "戊": (MajorStarName.TANLANG, MajorStarName.TAIYIN,
          AuxiliaryStarName.YOUBI, MajorStarName.TIANJI),
    "己": (MajorStarName.WUQU, MajorStarName.TANLANG,
          MajorStarName.TIANLIANG, AuxiliaryStarName.WENQU),
    "庚": (MajorStarName.TAIYANG, MajorStarName.WUQU,
          MajorStarName.TAIYIN, MajorStarName.TIANTONG),
    "辛": (MajorStarName.JUMEN, MajorStarName.TAIYANG,
          AuxiliaryStarName.WENQU, AuxiliaryStarName.WENCHANG),
    "壬": (MajorStarName.TIANLIANG, MajorStarName.ZIWEI,
          MajorStarName.TIANFU, MajorStarName.WUQU),
    "癸": (MajorStarName.POJUN, MajorStarName.JUMEN,
          MajorStarName.TAIYIN, MajorStarName.TANLANG),
})


def transformation_targets(stem: HeavenlyStem) -> tuple[TransformationStarName, ...]:
    """Return the frozen four-name row without calculating any positions."""
    if type(stem) is not str or stem not in BIRTH_YEAR_TRANSFORMATION_TARGETS:
        raise ValueError("year stem must be a canonical Heavenly Stem")
    return BIRTH_YEAR_TRANSFORMATION_TARGETS[stem]


def _locate_target(target: TransformationStarName, existing: list[tuple]) -> tuple:
    matches = [row for row in existing if row[0] == target]
    if len(matches) != 1:
        raise ValueError(
            f"transformation target {target.value} must exist exactly once in the natal star set"
        )
    return matches[0]


def calculate_birth_year_transformations(
    calendar: CalendarResult,
    palace_layout: PalaceLayout,
    major_stars: MajorStarChart,
    auxiliary_stars: AuxiliaryStarChart,
) -> BirthYearTransformations:
    """Attach the primary birth-year row to existing natal star placements."""
    if not isinstance(calendar, CalendarResult):
        raise ValueError("calendar must be a validated CalendarResult object")
    if not isinstance(palace_layout, PalaceLayout):
        raise ValueError("palace_layout must be a validated PalaceLayout object")
    if not isinstance(major_stars, MajorStarChart):
        raise ValueError("major_stars must be a validated MajorStarChart object")
    if not isinstance(auxiliary_stars, AuxiliaryStarChart):
        raise ValueError("auxiliary_stars must be a validated AuxiliaryStarChart object")

    calendar = CalendarResult.model_validate(calendar.model_dump(round_trip=True))
    palace_layout = PalaceLayout.model_validate(palace_layout.model_dump(round_trip=True))
    major_stars = MajorStarChart.model_validate(major_stars.model_dump(round_trip=True))
    auxiliary_stars = AuxiliaryStarChart.model_validate(auxiliary_stars.model_dump(round_trip=True))

    existing = [
        (row.name, row.earthly_branch, StarCategory.MAJOR) for row in major_stars.stars
    ] + [
        (row.name, row.earthly_branch, StarCategory.AUXILIARY)
        for row in auxiliary_stars.stars
    ]
    stem = calendar.year_ganzhi.heavenly_stem
    records = []
    for transformation, target in zip(TRANSFORMATION_ORDER, transformation_targets(stem), strict=True):
        _, branch, category = _locate_target(target, existing)
        palace_matches = [row for row in palace_layout.palaces if row.earthly_branch == branch]
        if len(palace_matches) != 1:
            raise ValueError(f"target branch {branch} must resolve to exactly one natal palace")
        records.append(BirthYearTransformation(
            transformation=transformation,
            star_name=target,
            earthly_branch=branch,
            palace_name=palace_matches[0].name,
            star_category=category,
        ))
    return BirthYearTransformations(year_heavenly_stem=stem, transformations=tuple(records))
