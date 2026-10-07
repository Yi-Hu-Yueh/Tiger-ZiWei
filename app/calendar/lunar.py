"""Deterministic Gregorian/lunar conversion using sxtwl 2.0.7."""

from datetime import date

import sxtwl

from app.models.calendar import LunarDate, SUPPORTED_GREGORIAN_START

# sxtwl's solar API uses the historical Julian/Gregorian cutover. Earlier
# dates would not match BirthData's Gregorian semantics; do not reinterpret them.
GREGORIAN_START = SUPPORTED_GREGORIAN_START


def _solar_day(solar_date: date) -> sxtwl.Day:
    if solar_date < GREGORIAN_START:
        raise ValueError("Gregorian conversion requires a date on or after 1582-10-15")
    return sxtwl.fromSolar(solar_date.year, solar_date.month, solar_date.day)


def _lunar_date(day: sxtwl.Day) -> LunarDate:
    return LunarDate(
        year=day.getLunarYear(True),
        month=day.getLunarMonth(),
        day=day.getLunarDay(),
        is_leap_month=day.isLunarLeap(),
    )


def to_lunar(solar_date: date) -> LunarDate:
    """Convert a Gregorian civil date; True explicitly selects lunar years."""
    return _lunar_date(_solar_day(solar_date))


def to_solar(lunar_date: LunarDate) -> date:
    """Convert a real lunar date, rejecting nonexistent leap months/days."""
    if lunar_date.is_leap_month and sxtwl.getRunMonth(lunar_date.year) != lunar_date.month:
        raise ValueError("the requested lunar leap month does not exist")
    length = sxtwl.getLunarMonthNum(
        lunar_date.year, lunar_date.month, lunar_date.is_leap_month,
    )
    if lunar_date.day > length:
        raise ValueError("day exceeds the actual lunar month length")
    day = sxtwl.fromLunar(
        lunar_date.year, lunar_date.month, lunar_date.day, lunar_date.is_leap_month,
    )
    solar_date = date(day.getSolarYear(), day.getSolarMonth(), day.getSolarDay())
    if to_lunar(solar_date) != lunar_date:
        raise ValueError("lunar conversion did not preserve the requested date")
    return solar_date
