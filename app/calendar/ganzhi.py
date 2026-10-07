"""Calendar assembly with explicit year, month, day and hour conventions."""

from datetime import date, time

import sxtwl

from app.calendar.lunar import _lunar_date, _solar_day, to_solar
from app.models.birth import BirthData
from app.models.calendar import (
    EARTHLY_BRANCHES,
    HEAVENLY_STEMS,
    CalendarResult,
    Ganzhi,
    LunarDate,
)


def _ganzhi(value: sxtwl.GZ) -> Ganzhi:
    if not (0 <= value.tg < 10 and 0 <= value.dz < 12):
        raise ValueError("calendar engine returned invalid Ganzhi indexes")
    return Ganzhi(
        heavenly_stem=HEAVENLY_STEMS[value.tg],
        earthly_branch=EARTHLY_BRANCHES[value.dz],
    )


def calculate_lunar_year_ganzhi(lunar_year: int) -> Ganzhi:
    """Return the year Ganzhi for one explicit Chinese lunar year.

    The conversion deliberately enters the existing Phase 1B path through
    lunar month 1, day 1.  This makes Lunar New Year the only year boundary;
    neither January 1 nor Li Chun is consulted.
    """

    if isinstance(lunar_year, bool) or not isinstance(lunar_year, int):
        raise ValueError("lunar year must be an integer")
    if not 1583 <= lunar_year <= 9999:
        raise ValueError("lunar year must be between 1583 and 9999")
    solar_date = to_solar(
        LunarDate(year=lunar_year, month=1, day=1, is_leap_month=False),
    )
    day = _solar_day(solar_date)
    if _lunar_date(day).year != lunar_year:
        raise ValueError("lunar year conversion did not preserve the requested year")
    return _ganzhi(day.getYearGZ(True))


def calculate_lunar_month_ganzhi(lunar_year: int, lunar_month: int) -> Ganzhi:
    """Return the traditional Ganzhi assigned to one numbered lunar month.

    This is the Five-Tigers month rule: month one is 寅 and its stem is
    derived from the lunar-year stem.  A leap month retains its numbered
    month's Ganzhi; Tiger's separate effective-month rule affects palace
    placement, not this canonical month label.
    """

    if isinstance(lunar_month, bool) or not isinstance(lunar_month, int):
        raise ValueError("lunar month must be an integer")
    if not 1 <= lunar_month <= 12:
        raise ValueError("lunar month must be between 1 and 12")
    year_stem = calculate_lunar_year_ganzhi(lunar_year).heavenly_stem
    first_month_stem_index = (HEAVENLY_STEMS.index(year_stem) * 2 + 2) % 10
    return Ganzhi(
        heavenly_stem=HEAVENLY_STEMS[(first_month_stem_index + lunar_month - 1) % 10],
        earthly_branch=EARTHLY_BRANCHES[(lunar_month + 1) % 12],
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
    return calculate_civil_calendar(solar_date, solar_time)


def calculate_civil_calendar(solar_date: date, solar_time: time) -> CalendarResult:
    """Calculate one explicitly supplied civil datetime through the shared engine."""

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
        hour_ganzhi=_ganzhi(day.getHourGZ(solar_time.hour, False)),
    )
