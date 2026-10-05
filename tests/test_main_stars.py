"""Phase 1E source-table, full-layout and upstream integration regressions."""

from collections import Counter
from datetime import date

import pytest
from pydantic import ValidationError

from app.calendar.ganzhi import calculate_calendar
from app.models.birth import BirthData
from app.models.calendar import EARTHLY_BRANCHES, LunarDate
from app.models.ziwei import FiveElementsBureauResult, MajorStarChart
from app.ziwei import calculate_five_elements_bureau, calculate_major_stars, calculate_palaces
from app.ziwei.five_elements import bureau_from_year_stem_and_life_branch
from app.ziwei.main_stars import (
    calculate_tianfu_position, calculate_ziwei_position, place_tianfu_group, place_ziwei_group,
)
from tests.major_star_reference import (
    CLASSICAL_CASES, CLASSICAL_CELLS, FULL_LAYOUTS, JAN29_MIDNIGHT,
    RAW_CLASSICAL_CELLS, STAR_NAMES, TIANFU_REFERENCE, WOOD_27,
)


def rule_chart(bureau: int, day: int) -> MajorStarChart:
    # Known Phase 1D rule inputs for each bureau, not a second bureau algorithm.
    branch = {2: "子", 3: "辰", 4: "申", 5: "午", 6: "寅"}[bureau]
    upstream = bureau_from_year_stem_and_life_branch("甲", branch)
    assert upstream.bureau_number == bureau
    return calculate_major_stars(LunarDate(year=2025, month=1, day=day, is_leap_month=False), upstream)


@pytest.mark.parametrize("bureau,expected", [(6, "酉"), (5, "午"), (4, "亥"), (3, "辰"), (2, "丑")])
def test_classical_five_day_one_anchors(bureau: int, expected: str) -> None:
    assert calculate_ziwei_position(1, bureau).earthly_branch == expected


@pytest.mark.parametrize("bureau,day,offset,quotient,base,expected", [
    (3, 27, 0, 9, "戌", "戌"),
    (6, 13, 5, 3, "辰", "亥"),
    (5, 6, 4, 2, "卯", "未"),
])
def test_published_iztro_examples_with_trace(
    bureau: int, day: int, offset: int, quotient: int, base: str, expected: str,
) -> None:
    result = calculate_ziwei_position(day, bureau)
    assert (result.offset, result.quotient, result.base_branch, result.earthly_branch) == (
        offset, quotient, base, expected,
    )
    chart = rule_chart(bureau, day)
    assert chart.star_to_branch == dict(zip(STAR_NAMES, FULL_LAYOUTS[expected], strict=True))


def test_reference_integrity_and_exact_source_errata() -> None:
    assert len(CLASSICAL_CASES) == len({(b, d) for b, d, _ in CLASSICAL_CASES}) == 150
    for bureau, cells in CLASSICAL_CELLS.items():
        days = [d for values in cells.values() for d in values]
        assert len(days) == 30 and set(days) == set(range(1, 31))
        assert set(cells) == set(EARTHLY_BRANCHES)
    # Preserve rather than hide the raw transcription defects.
    raw_wood = Counter(d for days in RAW_CLASSICAL_CELLS[3].values() for d in days)
    assert raw_wood[9] == 2 and raw_wood[5] == 0
    assert 30 not in {d for days in RAW_CLASSICAL_CELLS[4].values() for d in days}
    changes = [(b, p) for b in CLASSICAL_CELLS for p in CLASSICAL_CELLS[b]
               if CLASSICAL_CELLS[b][p] != RAW_CLASSICAL_CELLS[b][p]]
    assert set(changes) == {(3, "寅"), (4, "亥")}
    assert CLASSICAL_CELLS[3]["寅"] == (3, 5)
    assert CLASSICAL_CELLS[4]["亥"] == (1, 30)


@pytest.mark.parametrize("bureau,day,expected", CLASSICAL_CASES)
def test_all_150_classical_table_cases_and_complete_structure(bureau: int, day: int, expected: str) -> None:
    result = calculate_ziwei_position(day, bureau)
    assert result.earthly_branch == expected
    assert 0 <= result.offset < bureau
    assert (day + result.offset) % bureau == 0
    assert all((day + smaller) % bureau != 0 for smaller in range(result.offset))
    assert result.quotient * bureau == day + result.offset
    chart = rule_chart(bureau, day)
    assert len(chart.stars) == len({s.name for s in chart.stars}) == 14
    assert set(chart.star_to_branch) == set(STAR_NAMES)
    assert chart.star_to_branch == dict(zip(STAR_NAMES, FULL_LAYOUTS[expected], strict=True))
    assert chart.tianfu_branch == TIANFU_REFERENCE[expected]
    assert all(s.earthly_branch in EARTHLY_BRANCHES for s in chart.stars)


@pytest.mark.parametrize("day,bureau,offset,quotient,base,branch", [
    (2, 2, 0, 1, "寅", "寅"), (1, 2, 1, 1, "寅", "丑"),
    (1, 3, 2, 1, "寅", "辰"), (1, 4, 3, 1, "寅", "亥"),
    (1, 5, 4, 1, "寅", "午"), (1, 6, 5, 1, "寅", "酉"),
    (24, 2, 0, 12, "丑", "丑"), (30, 2, 0, 15, "辰", "辰"),
    (28, 3, 2, 10, "亥", "丑"),
])
def test_padding_parity_quotient_and_both_wrap_directions(
    day: int, bureau: int, offset: int, quotient: int, base: str, branch: str,
) -> None:
    r = calculate_ziwei_position(day, bureau)
    assert (r.offset, r.quotient, r.base_branch, r.earthly_branch) == (offset, quotient, base, branch)


@pytest.mark.parametrize("ziwei,tianfu", TIANFU_REFERENCE.items())
def test_all_twelve_tianfu_positions(ziwei: str, tianfu: str) -> None:
    assert calculate_tianfu_position(ziwei) == tianfu
    assert calculate_tianfu_position(tianfu) == ziwei
    assert (ziwei == tianfu) == (ziwei in ("寅", "申"))


@pytest.mark.parametrize("ziwei,layout", FULL_LAYOUTS.items())
def test_groups_at_all_twelve_rotations(ziwei: str, layout: str) -> None:
    # Fully static positions, not expected values generated by an offset helper.
    assert len(layout) == 14
    zgroup = place_ziwei_group(ziwei)
    fgroup = place_tianfu_group(TIANFU_REFERENCE[ziwei])
    assert [(s.name, s.earthly_branch) for s in zgroup] == list(zip(STAR_NAMES[:6], layout[:6], strict=True))
    assert [(s.name, s.earthly_branch) for s in fgroup] == list(zip(STAR_NAMES[6:], layout[6:], strict=True))
    zi = EARTHLY_BRANCHES.index(ziwei)
    fi = EARTHLY_BRANCHES.index(TIANFU_REFERENCE[ziwei])
    assert [(EARTHLY_BRANCHES.index(s.earthly_branch) - zi) % 12 for s in zgroup] == [0, 11, 9, 8, 7, 4]
    assert [(EARTHLY_BRANCHES.index(s.earthly_branch) - fi) % 12 for s in fgroup] == [0, 1, 2, 3, 4, 5, 6, 10]


def test_complete_wood_day_27_manual_vector_and_shared_palaces() -> None:
    chart = rule_chart(3, 27)
    assert chart.star_to_branch == WOOD_27
    assert chart.branch_to_stars["午"] == ("武曲", "天府")
    assert chart.branch_to_stars["戌"] == ("紫微", "天相")
    assert chart.branch_to_stars["丑"] == ()
    assert sum(len(stars) for stars in chart.branch_to_stars.values()) == 14


def integrated(solar: str, hour: int, minute: int):
    value = date.fromisoformat(solar)
    birth = BirthData(gender="female", birthplace="Taipei", birth_year=value.year,
                      birth_month=value.month, birth_day=value.day, birth_hour=hour, birth_minute=minute)
    cal = calculate_calendar(birth)
    palaces = calculate_palaces(cal)
    bureau = calculate_five_elements_bureau(cal, palaces)
    return cal, palaces, bureau, calculate_major_stars(cal.lunar_date, bureau)


# Manually traced from Phase 1B-1D references and classical birthday tables.
FULL_INPUTS = [
    ("2025-01-29", 0, 30, 1, False, "土五局", 5, "午", "戌"),
    ("2025-01-29", 1, 30, 1, False, "火六局", 6, "酉", "未"),
    ("2024-02-29", 12, 0, 20, False, "金四局", 4, "午", "戌"),
    ("2025-07-25", 12, 0, 1, True, "土五局", 5, "午", "戌"),
    ("2025-07-25", 14, 30, 1, True, "火六局", 6, "酉", "未"),
    ("2025-07-24", 23, 59, 30, False, "木三局", 3, "亥", "巳"),
    ("2025-07-25", 0, 0, 1, True, "水二局", 2, "丑", "卯"),
]


@pytest.mark.parametrize("solar,hour,minute,day,leap,name,number,ziwei,tianfu", FULL_INPUTS)
def test_full_birth_integration(
    solar: str, hour: int, minute: int, day: int, leap: bool, name: str,
    number: int, ziwei: str, tianfu: str,
) -> None:
    cal, palaces, bureau, chart = integrated(solar, hour, minute)
    assert cal.lunar_date.day == chart.lunar_day == day
    assert cal.lunar_date.is_leap_month is leap
    assert bureau.bureau_number == chart.bureau_number == number
    assert bureau.bureau_name == chart.bureau_name == name
    assert (chart.ziwei_branch, chart.tianfu_branch) == (ziwei, tianfu)
    assert chart.star_to_branch == dict(zip(STAR_NAMES, FULL_LAYOUTS[ziwei], strict=True))
    if leap:
        assert cal.lunar_date.month == 6 and palaces.effective_lunar_month == 7


def test_mandatory_jan29_complete_manual_layout() -> None:
    cal, layout, bureau, chart = integrated("2025-01-29", 0, 30)
    assert cal.lunar_date == LunarDate(year=2025, month=1, day=1, is_leap_month=False)
    assert cal.year_ganzhi.heavenly_stem == "乙"
    assert layout.life_palace_branch == "寅"
    assert bureau.life_palace_ganzhi.display == "戊寅"
    assert (bureau.bureau_name, bureau.bureau_number) == ("土五局", 5)
    assert chart.star_to_branch == JAN29_MIDNIGHT
    assert chart.branch_to_stars["戌"] == ("廉貞", "天府")


def test_leap_same_day_different_hour_consumes_different_upstream_bureau() -> None:
    a = integrated("2025-07-25", 12, 0)
    b = integrated("2025-07-25", 14, 30)
    assert a[0].lunar_date == b[0].lunar_date
    assert (a[1].life_palace_branch, b[1].life_palace_branch) == ("寅", "丑")
    assert (a[2].bureau_number, b[2].bureau_number) == (5, 6)
    assert (a[3].ziwei_branch, b[3].ziwei_branch) == ("午", "酉")


def test_late_zi_preserves_lunar_day_and_all_upstream_objects() -> None:
    cal, layout, bureau, chart = integrated("2025-07-24", 23, 59)
    before = (cal.model_dump(), layout.model_dump(), bureau.model_dump())
    assert cal.hour_ganzhi.earthly_branch == "子"
    assert cal.lunar_date.day == chart.lunar_day == 30
    assert chart.ziwei_branch == "亥"
    assert calculate_major_stars(cal.lunar_date, bureau) == chart
    assert before == (cal.model_dump(), layout.model_dump(), bureau.model_dump())
    midnight = integrated("2025-07-25", 0, 0)[3]
    assert (midnight.lunar_day, midnight.bureau_number, midnight.ziwei_branch) == (1, 2, "丑")


def test_star_layer_uses_only_supplied_day_and_bureau() -> None:
    cal, _, bureau, original = integrated("2025-01-29", 0, 30)
    # Synthetic lunar records with the same day must not introduce leap/year rules.
    different_month = LunarDate(year=2024, month=6, day=1, is_leap_month=True)
    assert calculate_major_stars(different_month, bureau) == original
    other_bureau = bureau_from_year_stem_and_life_branch("甲", "寅")
    assert calculate_major_stars(cal.lunar_date, other_bureau).ziwei_branch == "酉"


@pytest.mark.parametrize("day", [0, -1, 31, 100, True, 1.0, "1", None])
def test_invalid_lunar_day_rejected(day) -> None:
    with pytest.raises(ValueError, match="lunar day"):
        calculate_ziwei_position(day, 2)


@pytest.mark.parametrize("bureau", [0, 1, 7, -2, True, 2.0, "2", "七局", None])
def test_unsupported_bureau_number_rejected(bureau) -> None:
    with pytest.raises(ValueError, match="bureau number"):
        calculate_ziwei_position(1, bureau)


@pytest.mark.parametrize("branch", ["", "甲", "子時", "A", None, 0])
@pytest.mark.parametrize("fn", [calculate_tianfu_position, place_ziwei_group, place_tianfu_group])
def test_invalid_branch_rejected(branch, fn) -> None:
    with pytest.raises(ValueError, match="earthly branches"):
        fn(branch)


@pytest.mark.parametrize("bad", [None, 5, "七局", {"bureau_number": 5}])
def test_malformed_bureau_objects_rejected(bad) -> None:
    with pytest.raises(ValueError, match="FiveElementsBureauResult"):
        calculate_major_stars(LunarDate(year=2025, month=1, day=1, is_leap_month=False), bad)


def test_bypassed_upstream_validation_is_not_trusted() -> None:
    cal, _, bureau, _ = integrated("2025-01-29", 0, 30)
    for key, value in [("nayin_element", "風"), ("year_heavenly_stem", "A"),
                       ("life_palace_ganzhi", {"heavenly_stem": "甲", "earthly_branch": "丑"})]:
        malformed = bureau.model_copy(update={key: value})
        with pytest.raises(ValueError):
            calculate_major_stars(cal.lunar_date, malformed)
    with pytest.raises(ValueError):
        calculate_major_stars(cal.lunar_date, FiveElementsBureauResult.model_construct())
    for bad in [0, 31, True, "1"]:
        with pytest.raises(ValueError):
            calculate_major_stars(cal.lunar_date.model_copy(update={"day": bad}), bureau)
    with pytest.raises(ValueError, match="LunarDate"):
        calculate_major_stars(1, bureau)


@pytest.mark.parametrize("defect", ["missing", "extra", "duplicate", "unknown", "invalid_branch", "brightness"])
def test_incomplete_or_malformed_star_result_rejected(defect: str) -> None:
    payload = rule_chart(3, 27).model_dump(round_trip=True)
    stars = list(payload["stars"])
    if defect == "missing":
        stars.pop()
    elif defect == "extra":
        stars.append(dict(stars[0]))
    elif defect == "duplicate":
        stars[1]["name"] = stars[0]["name"]
    elif defect == "unknown":
        stars[0]["name"] = "文昌"
    elif defect == "invalid_branch":
        stars[0]["earthly_branch"] = "甲"
    else:
        stars[0]["brightness"] = "廟"
    with pytest.raises(ValidationError):
        MajorStarChart.model_validate({**payload, "stars": stars})


def test_immutable_chart_serialization_and_non_mutating_views() -> None:
    chart = rule_chart(3, 27)
    assert MajorStarChart.model_validate(chart.model_dump(round_trip=True)) == chart
    payload = chart.model_dump(mode="json")
    assert (payload["ziwei_branch"], payload["tianfu_branch"], payload["bureau_name"]) == ("戌", "午", "木三局")
    assert len(payload["stars"]) == 14
    with pytest.raises(ValidationError):
        chart.stars[0].earthly_branch = "子"
    view = chart.star_to_branch
    view["紫微"] = "子"
    assert chart.ziwei_branch == "戌"
