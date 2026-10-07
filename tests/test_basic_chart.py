"""Phase 1F complete-core composition and invariant tests."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.calendar.ganzhi import calculate_calendar
from app.models.basic_chart import BasicChartResult
from app.models.calendar import EARTHLY_BRANCHES
from app.models.ziwei import PalaceName, MajorStarName
from app.ziwei import calculate_basic_chart, calculate_five_elements_bureau, calculate_major_stars, calculate_palaces
from app.ziwei.five_elements import palace_heavenly_stems
from scripts.validate_basic_chart import birth, display, normalize
from tests.basic_chart_reference import STATIC_CHARTS, COMPARISON_INPUTS


@pytest.mark.parametrize("expected", STATIC_CHARTS)
def test_three_static_complete_charts(expected) -> None:
    chart = calculate_basic_chart(birth(expected["solar"],expected["hour"],expected["minute"],expected["gender"]))
    lunar = chart.lunar_date
    assert (lunar.year,lunar.month,lunar.day,lunar.is_leap_month) == expected["lunar"]
    assert tuple(g.display for g in (chart.year_ganzhi,chart.month_ganzhi,chart.day_ganzhi,chart.hour_ganzhi)) == expected["ganzhi"]
    assert (chart.life_palace_branch,chart.body_palace_branch,chart.body_palace_name) == (
        expected["life"],expected["body"],expected["body_name"])
    assert chart.five_elements_bureau.life_palace_ganzhi.display == expected["life_ganzhi"]
    assert (chart.five_elements_bureau.bureau_name,chart.five_elements_bureau.bureau_number) == expected["bureau"]
    assert [(p.earthly_branch,p.palace_name,p.palace_ganzhi.display,p.has_body_palace,
             tuple(s.name for s in p.major_stars)) for p in chart.palaces] == expected["palaces"]
    assert normalize(chart)["stars"] == {star:row[0] for row in expected["palaces"] for star in row[4]}


@pytest.mark.parametrize("solar,hour,minute", COMPARISON_INPUTS)
def test_upstream_identity_and_all_internal_invariants(solar,hour,minute) -> None:
    b = birth(solar,hour,minute)
    before = b.model_dump()
    chart = calculate_basic_chart(b)
    calendar = calculate_calendar(b)
    layout = calculate_palaces(calendar)
    bureau = calculate_five_elements_bureau(calendar,layout)
    stars = calculate_major_stars(calendar.lunar_date,bureau)
    assert chart.birth_data.model_dump() == before == b.model_dump()
    assert chart.calendar == calendar
    assert chart.palace_layout == layout
    assert chart.five_elements_bureau == bureau
    assert chart.major_star_chart == stars
    assert tuple(p.earthly_branch for p in chart.palaces) == EARTHLY_BRANCHES
    assert {p.palace_name for p in chart.palaces} == set(PalaceName)
    assert sum(p.is_life_palace for p in chart.palaces) == 1
    assert sum(p.has_body_palace for p in chart.palaces) == 1
    host = next(p for p in chart.palaces if p.has_body_palace)
    assert (host.earthly_branch,host.palace_name) == (chart.body_palace_branch,chart.body_palace_name)
    assert {p.earthly_branch:p.heavenly_stem for p in chart.palaces} == palace_heavenly_stems(calendar.year_ganzhi.heavenly_stem)
    life = next(p for p in chart.palaces if p.is_life_palace)
    assert life.palace_ganzhi == bureau.life_palace_ganzhi
    grouped = [s for p in chart.palaces for s in p.major_stars]
    assert len(grouped) == len({s.name for s in grouped}) == 14
    assert {s.name for s in grouped} == set(MajorStarName)
    assert all(s.earthly_branch == p.earthly_branch for p in chart.palaces for s in p.major_stars)


@pytest.mark.parametrize("solar,hour,minute", COMPARISON_INPUTS)
def test_determinism_roundtrip_and_gender_independence(solar,hour,minute) -> None:
    b = birth(solar,hour,minute)
    a,c,d = (calculate_basic_chart(b) for _ in range(3))
    assert a == c == d
    assert a.model_dump_json(round_trip=True) == c.model_dump_json(round_trip=True) == d.model_dump_json(round_trip=True)
    assert BasicChartResult.model_validate_json(a.model_dump_json(round_trip=True)) == a
    male = calculate_basic_chart(birth(solar,hour,minute,"male"))
    assert a.model_dump(exclude={"birth_data", "major_luck"}) == male.model_dump(
        exclude={"birth_data", "major_luck"}
    )
    assert a.major_luck.direction != male.major_luck.direction
    female_input,male_input = a.birth_data.model_dump(),male.birth_data.model_dump()
    assert female_input.pop("gender") == "female"
    assert male_input.pop("gender") == "male"
    assert female_input == male_input


def payload():
    return calculate_basic_chart(birth("2025-01-29",0,30)).model_dump(round_trip=True)


@pytest.mark.parametrize("defect", ["missing", "duplicate_branch", "order", "duplicate_name", "alias", "no_body", "two_bodies", "wrong_body", "stem", "missing_star", "duplicate_star", "wrong_star_branch", "moved_star"])
def test_composed_structure_rejects_tampering(defect) -> None:
    data = payload()
    p = list(data["palaces"])
    if defect == "missing": p.pop()
    elif defect == "duplicate_branch": p[0]["palace_ganzhi"] = dict(p[2]["palace_ganzhi"])
    elif defect == "order": p[0],p[1] = p[1],p[0]
    elif defect == "duplicate_name": p[0]["palace_name"] = "命宮"
    elif defect == "alias": p[7]["palace_name"] = "奴僕宮"
    elif defect == "no_body": p[2]["has_body_palace"] = False
    elif defect == "two_bodies": p[0]["has_body_palace"] = True
    elif defect == "wrong_body": p[2]["has_body_palace"],p[0]["has_body_palace"] = False,True
    elif defect == "stem": p[2]["palace_ganzhi"]["heavenly_stem"] = "丙"
    elif defect == "missing_star": p[0]["major_stars"] = ()
    elif defect == "duplicate_star": p[0]["major_stars"][0]["name"] = "紫微"
    elif defect == "wrong_star_branch": p[0]["major_stars"][0]["earthly_branch"] = "午"
    else:
        star = p[0]["major_stars"][0]
        p[0]["major_stars"] = ()
        star["earthly_branch"] = "未"
        p[7]["major_stars"] = (star,)
    data["palaces"] = p
    with pytest.raises(ValidationError): BasicChartResult.model_validate(data)


@pytest.mark.parametrize("defect", ["birth", "lunar", "year", "month", "day", "hour", "life_body", "bureau", "major_stars"])
def test_authoritative_upstream_identity_rejects_forgery(defect) -> None:
    data = payload()
    if defect == "birth": data["birth_data"]["birth_minute"] = 31
    elif defect == "lunar": data["calendar"]["lunar_date"]["day"] = 2
    elif defect in {"year","month","day","hour"}:
        data["calendar"][defect+"_ganzhi"] = {"heavenly_stem":"甲","earthly_branch":"子"}
    elif defect == "life_body":
        # Structurally valid Phase 1C payload for a DIFFERENT hour must not pass.
        other = calculate_basic_chart(birth("2025-01-29",1,30))
        data["palace_layout"] = other.palace_layout.model_dump(round_trip=True)
    elif defect == "bureau": data["five_elements_bureau"]["nayin_element"] = "水"
    else: data["major_star_chart"]["stars"][0]["earthly_branch"] = "子"
    with pytest.raises(ValidationError,match="identity mismatch"):
        BasicChartResult.model_validate(data)


@pytest.mark.parametrize("hour,minute,life,bureau,ziwei", [(12,0,"寅",5,"午"),(14,30,"丑",6,"酉")])
def test_leap_internal_manual_vectors_unchanged(hour,minute,life,bureau,ziwei) -> None:
    chart = calculate_basic_chart(birth("2025-07-25",hour,minute))
    assert (chart.lunar_date.month,chart.lunar_date.day,chart.lunar_date.is_leap_month) == (6,1,True)
    assert chart.palace_layout.effective_lunar_month == 7
    assert (chart.life_palace_branch,chart.five_elements_bureau.bureau_number,chart.major_star_chart.ziwei_branch) == (life,bureau,ziwei)


def test_late_zi_input_snapshot_and_readable_display() -> None:
    b = birth("2025-07-24",23,59)
    chart = calculate_basic_chart(b)
    assert chart.lunar_date.day == chart.major_star_chart.lunar_day == 30
    assert (chart.life_palace_branch,chart.body_palace_branch) == ("未","未")
    assert chart.five_elements_bureau.bureau_number == 3
    assert (chart.major_star_chart.ziwei_branch,chart.major_star_chart.tianfu_branch) == ("亥","巳")
    b.birth_hour = 0
    assert chart.birth_data.birth_hour == 23
    with pytest.raises(ValidationError): chart.birth_data.birth_hour = 0
    text = display(chart)
    assert "23:59" in text and "木三局" in text
    assert len([line for line in text.splitlines() if line[:1] in EARTHLY_BRANCHES and " | " in line]) == 12


@pytest.fixture(scope="module")
def external_report():
    # Optional on machines without the separate dev engine. The Phase 1F run
    # explicitly prepares it and must report zero skipped external cases.
    root = Path(__file__).resolve().parents[1]
    node = shutil.which("node")
    if not node or not (root/"tmp/phase1f-iztro/build-receipt.json").exists():
        pytest.skip("full iztro dev checkout/Node absent; run setup before external gate")
    process = subprocess.run([node,"tests/verify_iztro_basic_chart.cjs"],cwd=root,check=False,
                             capture_output=True,text=True,encoding="utf-8",
                             env={**os.environ,"TIGER_PYTHON":sys.executable})
    assert process.returncode == 0, process.stderr + process.stdout
    report = json.loads(process.stdout)
    assert report["revision"] == "2c7ef9be669df7b19d1799f4dce335fed3794f78"
    assert report["configuration"] == {"algorithm":"default","yearDivide":"normal","dayDivide":"current"}
    assert report["fixLeap"] is True
    assert len(report["results"]) == 8
    return report


@pytest.mark.parametrize("index", range(8))
def test_actual_pinned_full_engine_comparison(external_report,index) -> None:
    row = external_report["results"][index]
    if index < 6:
        assert row["classification"] == "FULL MATCH"
        assert row["tiger"] == row["external"]
        assert row["earliest_divergence"] is None
    else:
        assert row["classification"] == "DIFFERENT_CONVENTION"
        assert row["tiger"]["lunar_date"] == row["external"]["lunar_date"]
        assert row["tiger"]["year_ganzhi"] == row["external"]["year_ganzhi"]
        assert row["earliest_divergence"]["field"] == "life"
        assert row["earliest_divergence"]["cause"] == "LEAP_MONTH_CONVENTION"
        # Observed independent-engine outputs, matching its documented day-1
        # leap-month convention. A convention label cannot hide arbitrary output.
        e = row["external"]
        assert (e["life"],e["body"],e["bureau"]["number"],e["stars"]["紫微"]) == (
            ("丑","丑",6,"酉") if index == 6 else ("子","寅",6,"酉"))
