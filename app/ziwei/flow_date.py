"""Deterministic Flow-Month and Flow-Day placement for an explicit target."""

from datetime import datetime

from app.calendar.ganzhi import calculate_civil_calendar
from app.models.basic_chart import BasicChartResult
from app.models.calendar import EARTHLY_BRANCHES, EarthlyBranch
from app.models.calendar import Ganzhi
from app.models.flow_date import (
    FlowDateInput,
    FlowDateResult,
    FlowDayPalace,
    FlowDayResult,
    FlowDayTransformation,
    FlowMonthPalace,
    FlowMonthResult,
    FlowMonthTransformation,
)
from app.models.flow_year import FlowYearResult
from app.models.ziwei import StarCategory, TRANSFORMATION_ORDER
from app.ziwei.flow_year import FLOW_YEAR_PALACE_ORDER, calculate_flow_year, flow_year_palace_branches
from app.ziwei.transformations import _locate_target, transformation_targets


def flow_month_transformation_targets(stem):
    """Select the shared authoritative Four-Transformation row by month stem."""

    return transformation_targets(stem)


def flow_day_transformation_targets(stem):
    """Select the shared authoritative Four-Transformation row by day stem."""

    return transformation_targets(stem)


def _dynamic_transformations(chart: BasicChartResult, stem, model):
    host_by_branch = {palace.earthly_branch: palace for palace in chart.palaces}
    existing_stars = [
        (star.name, star.earthly_branch, StarCategory.MAJOR)
        for palace in chart.palaces for star in palace.major_stars
    ] + [
        (star.name, star.earthly_branch, StarCategory.AUXILIARY)
        for palace in chart.palaces for star in palace.auxiliary_stars
    ]
    records = []
    for transformation_type, target in zip(
        TRANSFORMATION_ORDER, transformation_targets(stem), strict=True
    ):
        _, branch, category = _locate_target(target, existing_stars)
        records.append(model(
            transformation_type=transformation_type,
            star_name=target,
            star_category=category,
            natal_branch=branch,
            natal_palace_name=host_by_branch[branch].palace_name,
        ))
    return tuple(records)


def effective_lunar_month(month: int, is_leap_month: bool) -> int:
    """Apply Tiger-ZiWei's whole-leap-month-as-next-month convention."""

    if isinstance(month, bool) or not isinstance(month, int) or not 1 <= month <= 12:
        raise ValueError("lunar month must be an integer from 1 through 12")
    if not isinstance(is_leap_month, bool):
        raise ValueError("leap-month state must be boolean")
    return month + int(is_leap_month)


def flow_month_life_branch(
    flow_year_life_branch: EarthlyBranch,
    birth_hour_branch: EarthlyBranch,
    birth_effective_month: int,
    target_effective_month: int,
) -> EarthlyBranch:
    """Locate Flow-Month Life Palace using the adopted branch-index formula."""

    if flow_year_life_branch not in EARTHLY_BRANCHES or birth_hour_branch not in EARTHLY_BRANCHES:
        raise ValueError("Flow-Month calculation requires canonical Earthly Branches")
    if isinstance(birth_effective_month, bool) or not isinstance(birth_effective_month, int):
        raise ValueError("birth effective month must be an integer")
    if isinstance(target_effective_month, bool) or not isinstance(target_effective_month, int):
        raise ValueError("target effective month must be an integer")
    index = (
        EARTHLY_BRANCHES.index(flow_year_life_branch)
        + EARTHLY_BRANCHES.index(birth_hour_branch)
        + target_effective_month
        - birth_effective_month
    ) % 12
    return EARTHLY_BRANCHES[index]


def flow_day_life_branch(
    flow_month_life_palace_branch: EarthlyBranch,
    target_lunar_day: int,
) -> EarthlyBranch:
    """Advance one branch per lunar day, with day one unchanged."""

    if flow_month_life_palace_branch not in EARTHLY_BRANCHES:
        raise ValueError("Flow-Day calculation requires a canonical Earthly Branch")
    if (
        isinstance(target_lunar_day, bool)
        or not isinstance(target_lunar_day, int)
        or not 1 <= target_lunar_day <= 30
    ):
        raise ValueError("target lunar day must be an integer from 1 through 30")
    index = (EARTHLY_BRANCHES.index(flow_month_life_palace_branch) + target_lunar_day - 1) % 12
    return EARTHLY_BRANCHES[index]


def calculate_flow_month(
    chart: BasicChartResult,
    flow_year: FlowYearResult,
    *,
    lunar_year: int,
    lunar_month: int,
    is_leap_month: bool,
    month_ganzhi: Ganzhi,
) -> FlowMonthResult:
    """Build Flow-Month from one normalized lunar month."""

    target_effective_month = effective_lunar_month(lunar_month, is_leap_month)
    month_life_branch = flow_month_life_branch(
        flow_year.flow_life_palace_branch,
        chart.hour_ganzhi.earthly_branch,
        chart.palace_layout.effective_lunar_month,
        target_effective_month,
    )
    host_by_branch = {palace.earthly_branch: palace for palace in chart.palaces}
    if set(host_by_branch) != set(EARTHLY_BRANCHES):
        raise ValueError("Flow-Date calculation requires all twelve natal palace branches")
    month_palaces = tuple(
        FlowMonthPalace(
            flow_palace_name=name,
            earthly_branch=branch,
            natal_palace_name=host_by_branch[branch].palace_name,
            natal_palace_ganzhi=host_by_branch[branch].palace_ganzhi,
        )
        for name, branch in zip(
            FLOW_YEAR_PALACE_ORDER,
            flow_year_palace_branches(month_life_branch),
            strict=True,
        )
    )
    month_host = host_by_branch[month_life_branch]
    return FlowMonthResult(
        lunar_year=lunar_year,
        lunar_month=lunar_month,
        is_leap_month=is_leap_month,
        effective_month=target_effective_month,
        month_ganzhi=month_ganzhi,
        flow_month_life_palace_branch=month_life_branch,
        natal_host_palace_name=month_host.palace_name,
        natal_host_palace_ganzhi=month_host.palace_ganzhi,
        palaces=month_palaces,
        transformations=_dynamic_transformations(
            chart, month_ganzhi.heavenly_stem, FlowMonthTransformation
        ),
    )


def calculate_flow_day(
    chart: BasicChartResult,
    flow_month: FlowMonthResult,
    *,
    lunar_year: int,
    lunar_month: int,
    lunar_day: int,
    is_leap_month: bool,
    day_ganzhi: Ganzhi,
) -> FlowDayResult:
    """Build Flow-Day from one normalized complete lunar date."""

    day_life_branch = flow_day_life_branch(
        flow_month.flow_month_life_palace_branch,
        lunar_day,
    )
    host_by_branch = {palace.earthly_branch: palace for palace in chart.palaces}
    if set(host_by_branch) != set(EARTHLY_BRANCHES):
        raise ValueError("Flow-Date calculation requires all twelve natal palace branches")
    day_palaces = tuple(
        FlowDayPalace(
            flow_palace_name=name,
            earthly_branch=branch,
            natal_palace_name=host_by_branch[branch].palace_name,
            natal_palace_ganzhi=host_by_branch[branch].palace_ganzhi,
        )
        for name, branch in zip(
            FLOW_YEAR_PALACE_ORDER,
            flow_year_palace_branches(day_life_branch),
            strict=True,
        )
    )
    day_host = host_by_branch[day_life_branch]
    return FlowDayResult(
        target_lunar_year=lunar_year,
        target_lunar_month=lunar_month,
        target_lunar_day=lunar_day,
        target_is_leap_month=is_leap_month,
        day_ganzhi=day_ganzhi,
        flow_day_life_palace_branch=day_life_branch,
        natal_host_palace_name=day_host.palace_name,
        natal_host_palace_ganzhi=day_host.palace_ganzhi,
        palaces=day_palaces,
        transformations=_dynamic_transformations(
            chart, day_ganzhi.heavenly_stem, FlowDayTransformation
        ),
    )


def calculate_flow_date(chart: BasicChartResult, target: FlowDateInput) -> FlowDateResult:
    """Build Flow-Year, Flow-Month, and Flow-Day from one explicit civil target."""

    if not isinstance(chart, BasicChartResult):
        raise ValueError("chart must be a validated BasicChartResult")
    if not isinstance(target, FlowDateInput):
        raise ValueError("target must be a validated FlowDateInput")
    birth_datetime = datetime.combine(chart.calendar.solar_date, chart.calendar.solar_time)
    if target.value < birth_datetime:
        raise ValueError("target datetime cannot be earlier than the normalized birth datetime")

    target_calendar = calculate_civil_calendar(target.value.date(), target.value.time())
    lunar = target_calendar.lunar_date
    flow_year = calculate_flow_year(chart, lunar.year)
    flow_month = calculate_flow_month(
        chart,
        flow_year,
        lunar_year=lunar.year,
        lunar_month=lunar.month,
        is_leap_month=lunar.is_leap_month,
        month_ganzhi=target_calendar.month_ganzhi,
    )
    flow_day = calculate_flow_day(
        chart,
        flow_month,
        lunar_year=lunar.year,
        lunar_month=lunar.month,
        lunar_day=lunar.day,
        is_leap_month=lunar.is_leap_month,
        day_ganzhi=target_calendar.day_ganzhi,
    )
    return FlowDateResult(
        target_solar_datetime=target.value,
        target_lunar_year=lunar.year,
        target_lunar_month=lunar.month,
        target_lunar_day=lunar.day,
        target_is_leap_month=lunar.is_leap_month,
        target_effective_month=flow_month.effective_month,
        flow_year=flow_year,
        flow_month=flow_month,
        flow_day=flow_day,
    )
