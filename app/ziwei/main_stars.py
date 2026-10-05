"""Phase 1E deterministic major stars, following Quan Shu vol.2.

Primary: https://zh.wikisource.org/zh-hant/紫微斗數全書/卷二
Birthday/bureau tables, 安南北斗諸星訣 and 安天府圖.
Only upstream lunar day and bureau are consumed; there is no calendar,
leap-month, late-Zi, Life Palace, Na Yin or bureau calculation here.
"""

from dataclasses import dataclass

from app.models.calendar import EARTHLY_BRANCHES, EarthlyBranch, LunarDate
from app.models.ziwei import (
    FiveElementsBureauResult, MajorStarChart, MajorStarName, MajorStarPlacement,
)


@dataclass(frozen=True)
class ZiweiPosition:
    """Calculation trace for independent offset/quotient verification."""

    offset: int
    quotient: int
    base_branch: EarthlyBranch
    earthly_branch: EarthlyBranch


def calculate_ziwei_position(lunar_day: int, bureau_number: int) -> ZiweiPosition:
    """Count 寅 as one; even padding advances, odd padding retreats."""
    if type(lunar_day) is not int or not 1 <= lunar_day <= 30:
        raise ValueError("lunar day must be an integer from 1 through 30")
    if type(bureau_number) is not int or bureau_number not in (2, 3, 4, 5, 6):
        raise ValueError("bureau number must be an integer in {2, 3, 4, 5, 6}")
    offset = (-lunar_day) % bureau_number  # Smallest nonnegative padding.
    quotient = (lunar_day + offset) // bureau_number
    base_index = (EARTHLY_BRANCHES.index("寅") + quotient - 1) % 12
    displacement = offset if offset % 2 == 0 else -offset
    return ZiweiPosition(
        offset=offset, quotient=quotient,
        base_branch=EARTHLY_BRANCHES[base_index],
        earthly_branch=EARTHLY_BRANCHES[(base_index + displacement) % 12],
    )


def _branch_index(branch: EarthlyBranch) -> int:
    if branch not in EARTHLY_BRANCHES:
        raise ValueError("position must be one of the twelve earthly branches")
    return EARTHLY_BRANCHES.index(branch)


def calculate_tianfu_position(ziwei_branch: EarthlyBranch) -> EarthlyBranch:
    """Reflect 紫微 across the 寅/申 axis: canonical index -> (4 - index) % 12."""
    index = _branch_index(ziwei_branch)
    return EARTHLY_BRANCHES[(2 * EARTHLY_BRANCHES.index("寅") - index) % 12]


ZIWEI_GROUP = (
    (MajorStarName.ZIWEI, 0), (MajorStarName.TIANJI, -1),
    (MajorStarName.TAIYANG, -3), (MajorStarName.WUQU, -4),
    (MajorStarName.TIANTONG, -5), (MajorStarName.LIANZHEN, -8),
)
TIANFU_GROUP = (
    (MajorStarName.TIANFU, 0), (MajorStarName.TAIYIN, 1),
    (MajorStarName.TANLANG, 2), (MajorStarName.JUMEN, 3),
    (MajorStarName.TIANXIANG, 4), (MajorStarName.TIANLIANG, 5),
    (MajorStarName.QISHA, 6), (MajorStarName.POJUN, 10),
)


def _place_group(
    branch: EarthlyBranch, offsets: tuple[tuple[MajorStarName, int], ...],
) -> tuple[MajorStarPlacement, ...]:
    start = _branch_index(branch)
    return tuple(MajorStarPlacement(name=name, earthly_branch=EARTHLY_BRANCHES[(start + offset) % 12])
                 for name, offset in offsets)


def place_ziwei_group(ziwei_branch: EarthlyBranch) -> tuple[MajorStarPlacement, ...]:
    return _place_group(ziwei_branch, ZIWEI_GROUP)


def place_tianfu_group(tianfu_branch: EarthlyBranch) -> tuple[MajorStarPlacement, ...]:
    return _place_group(tianfu_branch, TIANFU_GROUP)


def calculate_major_stars(
    lunar_date: LunarDate, bureau: FiveElementsBureauResult,
) -> MajorStarChart:
    """Use Phase 1B LunarDate and Phase 1D bureau from the same birth input.

    Revalidate structure even if an upstream instance was built using Pydantic
    bypass helpers. Semantic provenance remains the upstream caller's contract;
    this function must not recalculate Life Palace, Ganzhi, Na Yin or bureau.
    Only lunar_date.day and the already-resolved bureau affect placement.
    """
    if not isinstance(lunar_date, LunarDate):
        raise ValueError("lunar_date must be a verified LunarDate result")
    if not isinstance(bureau, FiveElementsBureauResult):
        raise ValueError("bureau must be a verified FiveElementsBureauResult")
    lunar_date = LunarDate.model_validate(lunar_date.model_dump(round_trip=True, warnings=False))
    bureau = FiveElementsBureauResult.model_validate(bureau.model_dump(round_trip=True, warnings=False))
    ziwei = calculate_ziwei_position(lunar_date.day, bureau.bureau_number).earthly_branch
    tianfu = calculate_tianfu_position(ziwei)
    return MajorStarChart(
        lunar_day=lunar_date.day, bureau_element=bureau.nayin_element,
        stars=place_ziwei_group(ziwei) + place_tianfu_group(tianfu),
    )
