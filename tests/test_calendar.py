"""Independent Phase 1B reference vectors, with no network dependency.

CWA 2025 astronomical almanac (retrieved 2026-10-05):
https://www.cwa.gov.tw/Data/service/notice/download/Publish_20241209150048.pdf
Printed p.170 (PDF p.175): lunar month starts and lengths for 2023-2025.
Printed p.12 (PDF p.17): 2025-01-28/29/30 lunar dates and day/year Ganzhi.
Printed p.6 (PDF p.11): JDN on 2025-01-01 = 2460677;
one-based sexagenary position = (JDN - 10) % 60, with 0 meaning position 60.
Printed p.4 (PDF p.9): Li Chun 2025-02-03 22:10, UTC+08.

HKO independent cross-checks:
https://www.hko.gov.hk/tc/gts/time/calendar/text/files/T2024c.txt
https://www.hko.gov.hk/tc/gts/time/calendar/text/files/T2025c.txt
https://www.hko.gov.hk/tc/gts/time/stemsandbranches.htm
HKO tables 3/5 supply hour periods/stems; table 4 supplies month stems.
Expected values below were transcribed/derived from these sources, NOT sxtwl.
"""

from datetime import date, time
from importlib.metadata import version

import pytest
import sxtwl
from pydantic import ValidationError

from app.calendar.ganzhi import calculate_calendar
from app.calendar.lunar import to_lunar, to_solar
from app.models.birth import BirthData
from app.models.calendar import CalendarResult, Ganzhi, LunarDate


def calendar(solar: str, hour: int = 12, minute: int = 0) -> CalendarResult:
    civil_date = date.fromisoformat(solar)
    return calculate_calendar(BirthData(
        gender="female", birth_year=civil_date.year, birth_month=civil_date.month,
        birth_day=civil_date.day, birth_hour=hour, birth_minute=minute,
        birthplace="Taipei",
    ))


# Lunar dates from CWA p.170 month starts/lengths, cross-checked against HKO.
LUNAR_VECTORS = [
    ("2024-02-09", (2023, 12, 30, False)),
    ("2024-02-10", (2024, 1, 1, False)),
    ("2024-02-29", (2024, 1, 20, False)),
    ("2025-01-01", (2024, 12, 2, False)),
    ("2025-01-28", (2024, 12, 29, False)),
    ("2025-01-29", (2025, 1, 1, False)),
    ("2025-01-30", (2025, 1, 2, False)),
    ("2025-02-02", (2025, 1, 5, False)),
    ("2025-02-03", (2025, 1, 6, False)),
    ("2025-06-25", (2025, 6, 1, False)),
    ("2025-07-24", (2025, 6, 30, False)),
    ("2025-07-25", (2025, 6, 1, True)),
    ("2025-08-22", (2025, 6, 29, True)),
    ("2025-08-23", (2025, 7, 1, False)),
    ("2025-10-10", (2025, 8, 19, False)),
]


@pytest.mark.parametrize("solar,expected", LUNAR_VECTORS)
def test_lunar_matches_independent_reference(
    solar: str, expected: tuple[int, int, int, bool],
) -> None:
    actual = to_lunar(date.fromisoformat(solar))
    assert (actual.year, actual.month, actual.day, actual.is_leap_month) == expected


@pytest.mark.parametrize("solar,expected", LUNAR_VECTORS)
def test_lunar_reverse_and_round_trip(
    solar: str, expected: tuple[int, int, int, bool],
) -> None:
    civil_date = date.fromisoformat(solar)
    lunar = LunarDate(
        year=expected[0], month=expected[1], day=expected[2], is_leap_month=expected[3],
    )
    assert to_solar(lunar) == civil_date
    assert to_solar(to_lunar(civil_date)) == civil_date


@pytest.mark.parametrize("solar,expected", [
    ("2024-02-09", "癸卯"),  # After Li Chun, but before Lunar New Year.
    ("2024-02-10", "甲辰"),
    ("2025-01-28", "甲辰"),
    ("2025-01-29", "乙巳"),  # Before Li Chun, but already the new lunar year.
    ("2025-01-30", "乙巳"),
])
def test_year_uses_lunar_new_year(solar: str, expected: str) -> None:
    assert calendar(solar).year_ganzhi.display == expected


# CWA p.6 anchor/method gives these day values independently of the engine.
# CWA p.12 also explicitly prints the January 28-30 values.
@pytest.mark.parametrize("solar,expected", [
    ("2024-02-29", "癸亥"),
    ("2025-01-01", "庚午"),
    ("2025-01-28", "丁酉"),
    ("2025-01-29", "戊戌"),
    ("2025-01-30", "己亥"),
    ("2025-07-25", "乙未"),
    ("2025-08-23", "甲子"),
    ("2025-10-10", "壬子"),  # CWA's explicit worked example.
])
def test_day_ganzhi_independent_values(solar: str, expected: str) -> None:
    assert calendar(solar).day_ganzhi.display == expected


def test_cwa_julian_day_method_independent_of_sxtwl() -> None:
    # Python date subtraction and CWA's published anchor; no sxtwl oracle.
    # Includes residue zero (癸亥), which must not be off by one.
    stems = "甲乙丙丁戊己庚辛壬癸"
    branches = "子丑寅卯辰巳午未申酉戌亥"
    for solar, _ in LUNAR_VECTORS:
        jdn = 2460677 + (date.fromisoformat(solar) - date(2025, 1, 1)).days
        position = (jdn - 10) % 60
        expected = stems[(position - 1) % 10] + branches[(position - 1) % 12]
        assert calendar(solar).day_ganzhi.display == expected


@pytest.mark.parametrize("solar,hour,expected", [
    ("2025-02-02", 23, "丁丑"),
    ("2025-02-03", 23, "戊寅"),
    ("2025-02-04", 0, "戊寅"),
])
def test_month_boundary_independent_reference(solar: str, hour: int, expected: str) -> None:
    # CWA Li Chun date/time + HKO table 4: preceding Jia year Chou = Ding;
    # new Yi year Yin = Wu. These times are unambiguously either side of Li Chun.
    assert calendar(solar, hour).month_ganzhi.display == expected


def test_month_is_date_granular_and_separate_from_lunar_month() -> None:
    # An ENGINE CONVENTION test, not an independent exact-instant oracle.
    # The official term instant is 22:10; sxtwl changes already at 00:00.
    before = calendar("2025-02-02", 23, 59)
    start = calendar("2025-02-03", 0, 0)
    end = calendar("2025-02-03", 23, 59)
    assert before.month_ganzhi.display == "丁丑"
    assert start.month_ganzhi.display == end.month_ganzhi.display == "戊寅"
    assert before.lunar_date.month == start.lunar_date.month == 1
    assert start.month_boundary == "solar_term_civil_date"


@pytest.mark.parametrize("hour,minute,expected", [
    (0, 0, "壬子"), (0, 59, "壬子"),
    (1, 0, "癸丑"), (2, 59, "癸丑"), (3, 0, "甲寅"),
    (10, 59, "丁巳"), (11, 0, "戊午"), (12, 59, "戊午"),
    (13, 0, "己未"), (20, 59, "壬戌"), (21, 0, "癸亥"),
    (22, 59, "癸亥"), (23, 0, "壬子"), (23, 59, "壬子"),
])
def test_hour_from_civil_day_and_hko_table(hour: int, minute: int, expected: str) -> None:
    # CWA: 2025-01-29 is 戊戌. HKO table 5 戊/癸 row supplies stems.
    result = calendar("2025-01-29", hour, minute)
    assert result.hour_ganzhi.display == expected
    assert result.solar_time == time(hour, minute)
    assert result.day_ganzhi.display == "戊戌"
    assert result.solar_date == date(2025, 1, 29)
    assert result.lunar_date.day == 1


def test_midnight_advances_only_when_input_civil_date_changes() -> None:
    last = calendar("2025-01-29", 23, 59)
    next_day = calendar("2025-01-30", 0, 0)
    assert last.day_ganzhi.display == "戊戌"
    assert last.hour_ganzhi.display == "壬子"
    assert next_day.day_ganzhi.display == "己亥"
    assert next_day.hour_ganzhi.display == "甲子"  # HKO table 5 己 row.
    assert next_day.lunar_date.day == 2


def test_installed_engine_api_and_late_zi_default_are_visible() -> None:
    # Compatibility/behavior probe only; this is not an independent oracle.
    assert version("sxtwl") == "2.0.7"
    day = sxtwl.fromSolar(2025, 1, 29)
    assert (day.getYearGZ(True).tg, day.getYearGZ(False).tg) == (1, 0)
    assert (day.getHourGZ(23).tg, day.getHourGZ(23).dz) == (0, 0)  # 甲子
    assert (day.getHourGZ(23, False).tg, day.getHourGZ(23, False).dz) == (8, 0)
    assert day.getDayGZ().tg == 4  # The day itself is still 戊戌 in both modes.


@pytest.mark.parametrize("stem,branch", [("A", "子"), ("甲", "x"), ("甲", "丑")])
def test_invalid_ganzhi_rejected(stem: str, branch: str) -> None:
    with pytest.raises(ValidationError):
        Ganzhi(heavenly_stem=stem, earthly_branch=branch)


def test_result_serialization_preserves_fields_and_policies() -> None:
    result = calendar("2025-07-25", 14, 30)
    payload = result.model_dump(mode="json")
    assert payload["lunar_date"] == {"year": 2025, "month": 6, "day": 1, "is_leap_month": True}
    for field in ("year_ganzhi", "month_ganzhi", "day_ganzhi", "hour_ganzhi"):
        assert payload[field]["heavenly_stem"] in "甲乙丙丁戊己庚辛壬癸"
        assert payload[field]["earthly_branch"] in "子丑寅卯辰巳午未申酉戌亥"
    assert payload["year_boundary"] == "lunar_new_year"
    assert payload["day_boundary"] == "civil_midnight"
    assert payload["time_basis"] == "supplied_civil_standard_time"
    assert payload["hour_policy"] == "civil_day_stem_no_23h_rollover"
    assert CalendarResult.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize("year,month,day,leap", [
    (2025, 5, 1, True), (2024, 6, 1, True), (2025, 6, 30, True),
    (2025, 2, 30, False),
])
def test_nonexistent_lunar_date_rejected(year: int, month: int, day: int, leap: bool) -> None:
    with pytest.raises(ValueError):
        to_solar(LunarDate(year=year, month=month, day=day, is_leap_month=leap))


@pytest.mark.parametrize("field,value", [
    ("year", 0), ("month", 0), ("month", 13), ("day", 0), ("day", 31),
    ("is_leap_month", "false"),
])
def test_invalid_lunar_structure_rejected(field: str, value: object) -> None:
    values: dict[str, object] = {"year": 2025, "month": 6, "day": 1, "is_leap_month": False}
    values[field] = value
    with pytest.raises(ValidationError):
        LunarDate.model_validate(values)


def test_historical_julian_dates_are_not_silently_treated_as_gregorian() -> None:
    # Concrete sxtwl cutover behavior motivating the documented lower bound.
    assert sxtwl.fromSolar(1582, 10, 4).after(1).getSolarDay() == 15
    with pytest.raises(ValueError, match="1582-10-15"):
        to_lunar(date(1582, 10, 14))
    with pytest.raises(ValueError, match="1582-10-15"):
        calendar("1500-03-01")
    assert to_solar(to_lunar(date(1582, 10, 15))) == date(1582, 10, 15)
