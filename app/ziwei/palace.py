"""Quan Shu vol.2: 安身命例 and 安十二宮例, with leap months as next month.

Rule text: https://zh.wikisource.org/zh-hant/紫微斗數全書/卷二
This module consumes calendar results; it performs no calendar conversion.
"""

from app.models.calendar import EARTHLY_BRANCHES, CalendarResult, EarthlyBranch, LunarDate
from app.models.ziwei import PALACE_ORDER, PalaceLayout, PalacePosition


def effective_lunar_month(lunar_date: LunarDate) -> int:
    """Tiger-ZiWei adopted natal leap-month convention; preserve LunarDate.

    Shared by Life/Body and, since Phase 2A-R, natal 左輔/右弼 placement.
    """
    effective_month = lunar_date.month + int(lunar_date.is_leap_month)
    if effective_month > 12:
        raise ValueError("leap month 12 palace placement is not supported; no month-13 rule adopted")
    return effective_month


def place_palaces(lunar_date: LunarDate, birth_hour_branch: EarthlyBranch) -> PalaceLayout:
    """Place Life backwards and Body forwards from 寅 + lunar month offset.

    The caller supplies an already validated lunar date (normally Phase 1B).
    Synthetic month/hour pairs may be used for classical rule tests. This
    function does not independently establish whether a lunar date exists.
    """
    if birth_hour_branch not in EARTHLY_BRANCHES:
        raise ValueError("birth hour must be one of the twelve earthly branches")
    month = effective_lunar_month(lunar_date)
    hour_index = EARTHLY_BRANCHES.index(birth_hour_branch)
    month_start = (EARTHLY_BRANCHES.index("寅") + month - 1) % 12
    life_index = (month_start - hour_index) % 12  # Count backwards from 子 hour.
    body_index = (month_start + hour_index) % 12  # Count forwards from 子 hour.

    positions = tuple(
        PalacePosition(
            name=name,
            earthly_branch=EARTHLY_BRANCHES[(life_index - offset) % 12],
            has_body_palace=(life_index - offset) % 12 == body_index,
        )
        for offset, name in enumerate(PALACE_ORDER)
    )
    return PalaceLayout(
        effective_lunar_month=month,
        birth_hour_branch=birth_hour_branch,
        palaces=positions,
    )


def calculate_palaces(calendar_result: CalendarResult) -> PalaceLayout:
    """Use Phase 1B's lunar month/leap flag and structured hour branch.

    23:xx is 子 without advancing the supplied civil/lunar date. Neither
    Gregorian month nor month Ganzhi participates in palace placement.
    """
    return place_palaces(
        calendar_result.lunar_date,
        calendar_result.hour_ganzhi.earthly_branch,
    )
