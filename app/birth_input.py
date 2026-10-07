"""Normalize solar/lunar user entry into the one Gregorian chart input."""

from app.calendar.lunar import to_solar
from app.models.birth import BirthData, BirthInput, CalendarType
from app.models.calendar import LunarDate
from pydantic import ValidationError


class BirthInputConversionError(ValueError):
    """A safe Traditional-Chinese lunar-input validation error."""


def normalize_birth_input(value: BirthInput) -> BirthData:
    """Convert a validated entry to the existing authoritative BirthData."""

    common = {
        "name": value.name,
        "gender": value.gender,
        "birth_hour": value.birth_hour,
        "birth_minute": value.birth_minute,
        "birthplace": value.birthplace,
    }
    if value.calendar_type is CalendarType.SOLAR:
        try:
            return BirthData(
                **common,
                birth_year=value.birth_year,
                birth_month=value.birth_month,
                birth_day=value.birth_day,
            )
        except ValidationError:
            raise BirthInputConversionError("西元出生日期無效，請重新確認年月日。") from None

    lunar_date = LunarDate(
        year=value.lunar_year,
        month=value.lunar_month,
        day=value.lunar_day,
        is_leap_month=value.is_leap_month,
    )
    try:
        solar_date = to_solar(lunar_date)
    except ValueError as exc:
        if "leap month does not exist" in str(exc):
            message = "指定的農曆年份沒有該閏月。"
        else:
            message = "指定的農曆日期不存在。"
        raise BirthInputConversionError(message) from None
    return BirthData(
        **common,
        birth_year=solar_date.year,
        birth_month=solar_date.month,
        birth_day=solar_date.day,
    )
