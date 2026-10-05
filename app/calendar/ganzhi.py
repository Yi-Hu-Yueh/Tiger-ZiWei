"""Calendar assembly with explicit year, month, day and hour conventions."""

from datetime import date, time

import sxtwl

from app.calendar.lunar import _lunar_date, _solar_day
from app.models.birth import BirthData
from app.models.calendar import (
    EARTHLY_BRANCHES,
    HEAVENLY_STEMS,
    CalendarResult,
    Ganzhi,
)


def _ganzhi(value: sxtwl.GZ) -> Ganzhi:
    if not (0 <= value.tg < 10 and 0 <= value.dz < 12):
        raise ValueError("calendar engine returned invalid Ganzhi indexes")
    return Ganzhi(
        heavenly_stem=HEAVENLY_STEMS[value.tg],
        earthly_branch=EARTHLY_BRANCHES[value.dz],
    )


def calculate_calendar(birth: BirthData) -> CalendarResult:
    """Preserve the supplied civil date/time and calculate calendar fields.

    Year: Lunar New Year. Month: sxtwl's solar-term *date*, not instant.
    Day: civil midnight. Hour: current civil-day stem, including 23:00.
    Minutes are preserved; two-hour periods change only at whole hours.
    No timezone lookup, true solar time, or Zi Wei late-Zi rule is applied.
    """
    solar_date = date(birth.birth_year, birth.birth_month, birth.birth_day)
    solar_time = time(birth.birth_hour, birth.birth_minute)
    day = _solar_day(solar_date)
    return CalendarResult(
        solar_date=solar_date,
        solar_time=solar_time,
        lunar_date=_lunar_date(day),
        year_ganzhi=_ganzhi(day.getYearGZ(True)),
        month_ganzhi=_ganzhi(day.getMonthGZ()),
        day_ganzhi=_ganzhi(day.getDayGZ()),
        # Default True advances the hour stem at 23:00. False explicitly
        # uses this civil day's stem for both occurrences of the Zi period.
        hour_ganzhi=_ganzhi(day.getHourGZ(birth.birth_hour, False)),
    )
