"""Normalize Gregorian/lunar query inputs and reuse deterministic flow engines."""

from datetime import date, time

from app.calendar.ganzhi import calculate_civil_calendar, calculate_lunar_month_ganzhi
from app.calendar.lunar import to_lunar, to_solar
from app.models.basic_chart import BasicChartResult
from app.models.calendar import LunarDate
from app.models.flow_query import (
    FlowQueryInput,
    FlowQueryResult,
    LunarFlowQueryInput,
    NormalizedFlowTarget,
    SolarFlowQueryInput,
)
from app.ziwei.flow_date import calculate_flow_day, calculate_flow_month, effective_lunar_month
from app.ziwei.flow_year import calculate_flow_year


def normalize_flow_target(query: FlowQueryInput) -> NormalizedFlowTarget:
    """Convert either public query mode into one canonical lunar target."""

    if isinstance(query, SolarFlowQueryInput):
        solar_date = date(query.year, query.month, query.day)
        lunar = to_lunar(solar_date)
        return NormalizedFlowTarget(
            input_mode="solar",
            original_solar_date=solar_date,
            original_is_leap_month=None,
            lunar_year=lunar.year,
            lunar_month=lunar.month,
            lunar_day=lunar.day,
            is_leap_month=lunar.is_leap_month,
            effective_month=effective_lunar_month(lunar.month, lunar.is_leap_month),
        )

    if not isinstance(query, LunarFlowQueryInput):
        raise ValueError("query must be a validated Gregorian or lunar flow query")
    converted_solar_date = None
    if query.month is not None and query.day is not None:
        converted_solar_date = to_solar(
            LunarDate(
                year=query.year,
                month=query.month,
                day=query.day,
                is_leap_month=query.is_leap_month,
            )
        )
    return NormalizedFlowTarget(
        input_mode="lunar",
        original_lunar_year=query.year,
        original_lunar_month=query.month,
        original_lunar_day=query.day,
        original_is_leap_month=query.is_leap_month,
        converted_solar_date=converted_solar_date,
        lunar_year=query.year,
        lunar_month=query.month,
        lunar_day=query.day,
        is_leap_month=query.is_leap_month,
        effective_month=(
            effective_lunar_month(query.month, query.is_leap_month)
            if query.month is not None
            else None
        ),
    )


def calculate_flow_query(chart: BasicChartResult, query: FlowQueryInput) -> FlowQueryResult:
    """Calculate only the dynamic layers justified by the query granularity."""

    if not isinstance(chart, BasicChartResult):
        raise ValueError("chart must be a validated BasicChartResult")
    target = normalize_flow_target(query)
    complete_solar_date = target.original_solar_date or target.converted_solar_date
    if complete_solar_date is not None and complete_solar_date < chart.calendar.solar_date:
        raise ValueError("target query date cannot be earlier than the normalized birth date")

    flow_year = calculate_flow_year(chart, target.lunar_year)
    flow_month = None
    flow_day = None
    if target.lunar_month is not None:
        calendar = (
            calculate_civil_calendar(complete_solar_date, time(0, 0))
            if complete_solar_date is not None
            else None
        )
        month_ganzhi = (
            calendar.month_ganzhi
            if calendar is not None
            else calculate_lunar_month_ganzhi(target.lunar_year, target.lunar_month)
        )
        flow_month = calculate_flow_month(
            chart,
            flow_year,
            lunar_year=target.lunar_year,
            lunar_month=target.lunar_month,
            is_leap_month=target.is_leap_month,
            month_ganzhi=month_ganzhi,
        )
        if target.lunar_day is not None:
            if calendar is None:
                raise ValueError("complete lunar query must provide an authoritative solar conversion")
            flow_day = calculate_flow_day(
                chart,
                flow_month,
                lunar_year=target.lunar_year,
                lunar_month=target.lunar_month,
                lunar_day=target.lunar_day,
                is_leap_month=target.is_leap_month,
                day_ganzhi=calendar.day_ganzhi,
            )

    return FlowQueryResult(
        query_mode=query.mode,
        original_query=query,
        normalized_target=target,
        flow_year=flow_year,
        flow_month=flow_month,
        flow_day=flow_day,
    )
