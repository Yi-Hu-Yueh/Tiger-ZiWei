"""Exhaustive static rules, structured-input integration and honest leap gating."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from pydantic import ValidationError

from app.calendar.ganzhi import calculate_calendar
from app.models.basic_chart import BasicChartResult
from app.models.calendar import CalendarResult, Ganzhi
from app.models.ziwei import AuxiliaryStarChart, AuxiliaryStarName
from app.ziwei.palace import effective_lunar_month
from app.ziwei import calculate_auxiliary_stars, calculate_basic_chart
from app.ziwei.auxiliary_stars import (
    place_left_right, place_chang_qu, place_kui_yue, place_lu_yang_tuo,
    place_tianma, place_huo_ling, place_kong_jie, calculate_year_hour_stars,
)
from scripts.validate_basic_chart import birth
from scripts.validate_auxiliary_stars import display
from tests.auxiliary_star_reference import (
    NAMES, BRANCHES, MONTH_ROWS, CHANG_QU_ROWS, KONG_JIE_ROWS, STEM_ROWS,
    HORSE_ROWS, FIRE_BELL_ROWS, FULL_CASES, LEAP_FULL, LEAP_YEAR_HOUR, LATE_ZI,
)


def branches(stars):
    result = tuple(s.earthly_branch for s in stars)
    assert all(b in BRANCHES for b in result)
    return result


@pytest.mark.parametrize("month,expected", tuple(enumerate(MONTH_ROWS, 1)))
def test_left_right_all_months(month, expected):
    assert branches(place_left_right(month)) == expected


@pytest.mark.parametrize("hour,expected", tuple(zip(BRANCHES, CHANG_QU_ROWS)))
def test_chang_qu_all_hours(hour, expected):
    assert branches(place_chang_qu(hour)) == expected


@pytest.mark.parametrize("row", STEM_ROWS)
def test_kui_yue_all_stems(row):
    stem, kui, yue, _, _, _ = row
    assert branches(place_kui_yue(stem)) == (kui, yue)


@pytest.mark.parametrize("row", STEM_ROWS)
def test_lu_yang_tuo_all_stems(row):
    stem, _, _, lu, yang, tuo = row
    assert branches(place_lu_yang_tuo(stem)) == (lu, yang, tuo)


@pytest.mark.parametrize("year,expected", HORSE_ROWS)
def test_tianma_all_branches(year, expected):
    assert branches(place_tianma(year)) == (expected,)


@pytest.mark.parametrize("year,hour,expected", [
    (year, hour, (fire[index], bell[index]))
    for years, fire, bell in FIRE_BELL_ROWS for year in years
    for index, hour in enumerate(BRANCHES)
])
def test_huo_ling_all_144_combinations(year, hour, expected):
    assert branches(place_huo_ling(year, hour)) == expected


def test_ren_chen_mao_mandatory_anchor():
    stars = calculate_year_hour_stars(Ganzhi(heavenly_stem="壬", earthly_branch="辰"), "卯")
    positions = {s.name: s.earthly_branch for s in stars}
    assert (positions["火星"], positions["鈴星"]) == ("巳", "丑")


@pytest.mark.parametrize("hour,expected", tuple(zip(BRANCHES, KONG_JIE_ROWS)))
def test_kong_jie_all_hours(hour, expected):
    assert branches(place_kong_jie(hour)) == expected


@pytest.mark.parametrize("label,solar,hour,minute,expected", FULL_CASES)
def test_full_static_cases_and_integration(label, solar, hour, minute, expected):
    b = birth(solar, hour, minute)
    calendar = calculate_calendar(b)
    before = calendar.model_dump_json(round_trip=True)
    auxiliary = calculate_auxiliary_stars(calendar)
    assert isinstance(auxiliary, AuxiliaryStarChart)
    assert auxiliary.star_to_branch == dict(zip(NAMES, expected))
    assert len(auxiliary.stars) == len(set(s.name for s in auxiliary.stars)) == 14
    assert calendar.model_dump_json(round_trip=True) == before
    chart = calculate_basic_chart(b)
    assert chart.auxiliary_star_chart == auxiliary
    assert len(chart.palaces) == 12
    assert sum(len(p.major_stars) for p in chart.palaces) == 14
    assert sum(len(p.auxiliary_stars) for p in chart.palaces) == 14
    for p in chart.palaces:
        assert tuple(s.name for s in p.auxiliary_stars) == auxiliary.branch_to_stars[p.earthly_branch]
        assert all(s.earthly_branch == p.earthly_branch for s in p.auxiliary_stars)
    assert BasicChartResult.model_validate_json(chart.model_dump_json(round_trip=True)) == chart
    assert chart.model_dump_json() == calculate_basic_chart(b).model_dump_json()
    assert all(name in display(chart) for name in NAMES)


def test_shared_palace_not_rejected_and_maps_are_copies():
    result = calculate_auxiliary_stars(calculate_calendar(birth("2025-01-29", 0, 30)))
    assert set(result.branch_to_stars["辰"]) == {"左輔", "文曲", "擎羊"}
    assert set(result.branch_to_stars["亥"]) == {"天馬", "地空", "地劫"}
    result.star_to_branch.clear()
    result.branch_to_stars.clear()
    assert len(result.stars) == 14 and len(result.branch_to_stars) == 12
    with pytest.raises(ValidationError):
        result.stars[0].earthly_branch = "子"
    with pytest.raises(ValidationError):
        result.stars = ()


@pytest.mark.parametrize("day", [1, 15, 16, 29, 30])
def test_whole_leap_month_next_month_no_day_15_split(day):
    calendar = calculate_calendar(birth("2025-07-25", 12, 0))
    data = calendar.model_dump(round_trip=True)
    data["lunar_date"]["day"] = day  # synthetic upstream rule input, not a conversion test
    calendar = CalendarResult.model_validate(data)
    before = calendar.model_dump_json(round_trip=True)
    auxiliary = calculate_auxiliary_stars(calendar)
    assert isinstance(auxiliary, AuxiliaryStarChart)
    assert auxiliary.status == "PASS"
    assert auxiliary.star_to_branch == LEAP_FULL
    assert {n: auxiliary.star_to_branch[n] for n in NAMES[2:]} == LEAP_YEAR_HOUR
    assert len(auxiliary.stars) == len(set(s.name for s in auxiliary.stars)) == 14
    assert effective_lunar_month(calendar.lunar_date) == 7
    assert calendar.model_dump_json(round_trip=True) == before
    assert AuxiliaryStarChart.model_validate_json(auxiliary.model_dump_json(round_trip=True)) == auxiliary
    with pytest.raises(ValidationError):
        AuxiliaryStarChart(stars=auxiliary.stars[2:])


def test_leap_basic_chart_keeps_phase1_and_completes_auxiliary():
    chart = calculate_basic_chart(birth("2025-07-25", 12, 0))
    assert (chart.lunar_date.month, chart.lunar_date.day, chart.lunar_date.is_leap_month) == (6, 1, True)
    assert chart.palace_layout.effective_lunar_month == 7
    assert chart.auxiliary_star_chart.status == "PASS"
    assert chart.auxiliary_star_chart.star_to_branch == LEAP_FULL
    assert sum(len(p.auxiliary_stars) for p in chart.palaces) == 14
    assert (chart.life_palace_branch, chart.body_palace_branch, chart.five_elements_bureau.bureau_number) == ("寅", "寅", 5)
    assert BasicChartResult.model_validate_json(chart.model_dump_json(round_trip=True)) == chart
    assert "左輔: 戌" in display(chart)
    assert "右弼: 辰" in display(chart)
    assert "實際農曆月: 6 / 閏月旗標: True" in display(chart)
    assert "有效本命月: 7" in display(chart)
    assert str(chart.calendar.solar_date) == "2025-07-25"
    assert chart.year_ganzhi.display == "乙巳"
    assert chart.major_star_chart.ziwei_branch == "午"
    assert chart.major_star_chart.tianfu_branch == "戌"


@pytest.mark.parametrize("month,leap,expected_month,expected", [
    (1, False, 1, ("辰", "戌")), (12, False, 12, ("卯", "亥")),
    (6, True, 7, ("戌", "辰")), (11, True, 12, ("卯", "亥")),
])
def test_shared_effective_month_path(monkeypatch, month, leap, expected_month, expected):
    data = calculate_calendar(birth("2025-07-25", 12, 0)).model_dump(round_trip=True)
    data["lunar_date"].update(month=month, is_leap_month=leap)
    calendar = CalendarResult.model_validate(data)
    calls = []
    def tracked(lunar):
        calls.append(lunar)
        return effective_lunar_month(lunar)
    monkeypatch.setattr("app.ziwei.auxiliary_stars.effective_lunar_month", tracked)
    auxiliary = calculate_auxiliary_stars(calendar)
    assert calls == [calendar.lunar_date]
    assert effective_lunar_month(calendar.lunar_date) == expected_month
    assert (auxiliary.star_to_branch["左輔"], auxiliary.star_to_branch["右弼"]) == expected
    assert {n: auxiliary.star_to_branch[n] for n in NAMES[2:]} == LEAP_YEAR_HOUR
    assert (calendar.lunar_date.month, calendar.lunar_date.is_leap_month) == (month, leap)


def test_unsupported_leap_twelfth_month_keeps_existing_guard():
    data = calculate_calendar(birth("2025-07-25", 12, 0)).model_dump(round_trip=True)
    data["lunar_date"]["month"] = 12
    with pytest.raises(ValueError, match="leap month 12"):
        calculate_auxiliary_stars(CalendarResult.model_validate(data))


def test_late_zi_no_upstream_mutation():
    calendar = calculate_calendar(birth("2025-07-24", 23, 59))
    before = calendar.model_dump_json(round_trip=True)
    result = calculate_auxiliary_stars(calendar)
    assert result.star_to_branch == LATE_ZI
    assert (calendar.lunar_date.month, calendar.lunar_date.day, calendar.lunar_date.is_leap_month) == (6, 30, False)
    assert calendar.year_ganzhi.display == "乙巳"
    assert calendar.hour_ganzhi.earthly_branch == "子"
    assert calendar.model_dump_json(round_trip=True) == before


@pytest.mark.parametrize("solar,expected", [("2025-01-28", ("丑", "未", "寅", "寅")),
                                          ("2025-01-29", ("子", "申", "卯", "亥"))])
def test_primary_lunar_new_year_not_gregorian_or_lichun(solar, expected):
    result = calculate_auxiliary_stars(calculate_calendar(birth(solar, 0, 30)))
    assert tuple(result.star_to_branch[n] for n in ("天魁", "天鉞", "祿存", "天馬")) == expected


@pytest.mark.parametrize("defect", ["missing", "duplicate", "extra", "bad_branch", "sky", "brightness"])
def test_exact_14_model_rejects_invalid(defect):
    data = calculate_auxiliary_stars(calculate_calendar(birth("2025-01-29", 0, 30))).model_dump(round_trip=True)
    stars = list(data["stars"])
    if defect == "missing": stars.pop()
    elif defect == "duplicate": stars[0]["name"] = stars[1]["name"]
    elif defect == "extra": stars.append(dict(stars[0]))
    elif defect == "bad_branch": stars[0]["earthly_branch"] = "甲"
    elif defect == "sky": stars[12]["name"] = "天空"
    else: stars[0]["brightness"] = "廟"
    data["stars"] = stars
    with pytest.raises(ValidationError): AuxiliaryStarChart.model_validate(data)


@pytest.mark.parametrize("defect", ["missing", "duplicate", "moved", "forged", "partial", "leap_full"])
def test_basic_auxiliary_tamper_rejected(defect):
    chart = calculate_basic_chart(birth("2025-07-25" if defect == "leap_full" else "2025-01-29", 0, 30))
    data = chart.model_dump(round_trip=True)
    if defect == "leap_full":
        data["auxiliary_star_chart"] = calculate_basic_chart(birth("2025-01-29", 0, 30)).auxiliary_star_chart.model_dump(round_trip=True)
    elif defect == "partial":
        data["auxiliary_star_chart"] = {"status": "INCONCLUSIVE", "stars": data["auxiliary_star_chart"]["stars"][2:]}
    elif defect == "forged":
        data["auxiliary_star_chart"]["stars"][0]["earthly_branch"] = "未"
    else:
        palace = data["palaces"][0]  # 天魁 is at 子 in A
        if defect == "missing": palace["auxiliary_stars"] = ()
        elif defect == "duplicate": palace["auxiliary_stars"] += palace["auxiliary_stars"]
        else:
            star = palace["auxiliary_stars"][0]
            palace["auxiliary_stars"] = ()
            star["earthly_branch"] = "丑"
            data["palaces"][1]["auxiliary_stars"] = (star,)
    with pytest.raises(ValidationError): BasicChartResult.model_validate(data)


@pytest.mark.parametrize("value", [0, 13, -1, True, 1.0, "1", None])
def test_invalid_month_rejected(value):
    with pytest.raises(ValueError): place_left_right(value)


@pytest.mark.parametrize("fn,args", [(place_chang_qu, ("甲",)), (place_kui_yue, ("子",)),
    (place_lu_yang_tuo, ("子",)), (place_tianma, ("甲",)), (place_huo_ling, ("辰", "甲")),
    (place_huo_ling, ("甲", "卯")), (place_kong_jie, ("甲",)),
    (calculate_auxiliary_stars, ({},)), (calculate_year_hour_stars, ({}, "子"))])
def test_invalid_inputs_rejected(fn, args):
    with pytest.raises(ValueError): fn(*args)


def test_no_upstream_calculators_called(monkeypatch):
    calendar = calculate_calendar(birth("2025-01-29", 0, 30))
    def forbidden(*args, **kwargs):
        raise AssertionError("auxiliary placement must only consume upstream data")
    for module, names in [("app.calendar.ganzhi", ["calculate_calendar"]),
                          ("app.calendar.lunar", ["to_lunar", "to_solar"]),
                          ("app.ziwei.palace", ["calculate_palaces"]),
                          ("app.ziwei.five_elements", ["calculate_five_elements_bureau"]),
                          ("app.ziwei.main_stars", ["calculate_major_stars"])]:
        for name in names: monkeypatch.setattr(f"{module}.{name}", forbidden)
    assert calculate_auxiliary_stars(calendar).status == "PASS"


def test_manual_cli_utf8_without_node():
    result = subprocess.run([sys.executable, "-m", "scripts.validate_auxiliary_stars"],
                            capture_output=True, cwd=Path(__file__).resolve().parents[1],
                            env={**os.environ, "PATH": "", "PYTHONIOENCODING": "cp950"})
    assert result.returncode == 0, result.stderr
    text = result.stdout.decode("utf-8").replace("\r\n", "\n")
    assert all(f"CASE {label}" in text for label in "ABCLZ")
    leap_text = text.split("CASE L\n")[1].split("CASE Z\n")[0]
    assert "左輔: 戌" in leap_text and "右弼: 辰" in leap_text
    assert "有效本命月: 7" in leap_text
    assert "INCONCLUSIVE" not in leap_text
    assert "2025年 閏6月1日" in text
    assert all(name in text for name in NAMES)


@pytest.fixture(scope="module")
def external_report():
    root = Path(__file__).resolve().parents[1]
    node = shutil.which("node")
    if not node or not (root / "tmp/phase1f-iztro/build-receipt.json").exists():
        pytest.skip("optional pinned iztro/Node dev engine absent; Python auxiliary tests need neither")
    result = subprocess.run([node, "tests/verify_iztro_auxiliary_stars.cjs"], cwd=root,
                            capture_output=True, text=True, encoding="utf-8",
                            env={**os.environ, "TIGER_PYTHON": sys.executable})
    assert result.returncode == 0, result.stderr + result.stdout
    return json.loads(result.stdout)


@pytest.mark.parametrize("label", ["A", "B", "C", "L", "Z"])
def test_optional_full_engine(external_report, label):
    assert external_report["revision"] == "2c7ef9be669df7b19d1799f4dce335fed3794f78"
    row = next(r for r in external_report["results"] if r["case"] == label)
    assert row["year_hour_stars_match"] is True
    assert row["status"] == ("DIFFERENT_CONVENTION" if label == "L" else "PASS")
    assert row["compared_count"] == 14
    if label == "L":
        assert (row["external"]["左輔"], row["external"]["右弼"]) == ("酉", "巳")
        assert row["tiger"] == LEAP_FULL
        assert row["differences"] == [
            {"name": "左輔", "tiger": "戌", "external": "酉"},
            {"name": "右弼", "tiger": "辰", "external": "巳"},
        ]
    else:
        assert row["differences"] == []
