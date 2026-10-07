"""Phase 6D deterministic Flow-Year Four Transformation contracts."""

import json
import os
from pathlib import Path
import shutil
import subprocess

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from app.birth_input import normalize_birth_input
from app.llm.nvidia_client import NvidiaClient
from app.main import app
from app.models.birth import BirthData, BirthInput
from app.models.calendar import HEAVENLY_STEMS
from app.models.flow_year import FlowYearResult, FlowYearTransformation
from app.models.ziwei import TRANSFORMATION_ORDER
from app.ziwei.basic_chart import calculate_basic_chart
from app.ziwei.flow_year import calculate_flow_year, flow_year_transformation_targets
from app.ziwei.major_luck import major_luck_transformation_targets
from app.ziwei.transformations import (
    BIRTH_YEAR_TRANSFORMATION_TARGETS,
    TRANSFORMATION_TARGETS_BY_STEM,
    _locate_target,
    transformation_targets,
)
from tests.flow_year_reference import CASE_A_FLOW_YEAR_TRANSFORMATIONS
from tests.transformation_reference import FORTY_ASSIGNMENTS, TEN_STEM_TABLE, TYPES


client = TestClient(app)
SOLAR_A = {
    "name": "預設 A", "gender": "female", "calendar_type": "solar",
    "birth_year": 2025, "birth_month": 1, "birth_day": 29,
    "birth_hour": 0, "birth_minute": 30, "birthplace": "Taipei",
}
LUNAR_A = {
    "name": "預設 A", "gender": "female", "calendar_type": "lunar",
    "lunar_year": 2025, "lunar_month": 1, "lunar_day": 1,
    "is_leap_month": False, "birth_hour": 0, "birth_minute": 30,
    "birthplace": "Taipei",
}
SOLAR_L = {
    "name": "預設 L", "gender": "female", "calendar_type": "solar",
    "birth_year": 2025, "birth_month": 7, "birth_day": 25,
    "birth_hour": 12, "birth_minute": 0, "birthplace": "Taipei",
}
LUNAR_L = {
    "name": "預設 L", "gender": "female", "calendar_type": "lunar",
    "lunar_year": 2025, "lunar_month": 6, "lunar_day": 1,
    "is_leap_month": True, "birth_hour": 12, "birth_minute": 0,
    "birthplace": "Taipei",
}


def case_a(gender: str = "female") -> BirthData:
    return BirthData(
        name="Case A", gender=gender, birth_year=2025, birth_month=1,
        birth_day=29, birth_hour=0, birth_minute=30, birthplace="Taipei",
    )


def normalized(result: FlowYearResult) -> tuple[tuple[str, str, str, str, str], ...]:
    return tuple(
        (
            item.transformation_type.value,
            item.star_name.value,
            item.star_category.value,
            item.earthly_branch,
            item.natal_palace_name.value,
        )
        for item in result.transformations
    )


def test_all_three_scopes_share_the_single_phase2b_table() -> None:
    assert BIRTH_YEAR_TRANSFORMATION_TARGETS is TRANSFORMATION_TARGETS_BY_STEM
    for stem in HEAVENLY_STEMS:
        shared = transformation_targets(stem)
        assert flow_year_transformation_targets(stem) is shared
        assert major_luck_transformation_targets(stem) is shared
        assert shared is TRANSFORMATION_TARGETS_BY_STEM[stem]
        assert tuple(item.value for item in shared) == TEN_STEM_TABLE[stem]


def test_all_ten_stems_have_the_exact_forty_phase2b_assignments() -> None:
    actual = tuple(
        (stem, transformation.value, star.value)
        for stem in HEAVENLY_STEMS
        for transformation, star in zip(
            TRANSFORMATION_ORDER, flow_year_transformation_targets(stem), strict=True,
        )
    )
    assert actual == FORTY_ASSIGNMENTS
    assert len(actual) == 40


@pytest.mark.parametrize("year", (2026, 2029, 2032, 2039))
def test_case_a_static_flow_year_transformation_fixtures(year: int) -> None:
    result = calculate_flow_year(calculate_basic_chart(case_a()), year)
    assert normalized(result) == CASE_A_FLOW_YEAR_TRANSFORMATIONS[year]
    assert len(result.transformations) == 4
    assert tuple(item.transformation_type for item in result.transformations) == TRANSFORMATION_ORDER


def test_2029_uses_flow_year_stem_not_birth_or_major_luck_stem() -> None:
    chart = calculate_basic_chart(case_a())
    result = calculate_flow_year(chart, 2029)
    assert (chart.calendar.year_ganzhi.heavenly_stem, result.heavenly_stem) == ("乙", "己")
    assert result.active_major_luck is not None
    assert result.active_major_luck.heavenly_stem == "戊"
    assert result.flow_life_palace_branch == "酉"
    flow_targets = tuple(item.star_name for item in result.transformations)
    assert flow_targets == transformation_targets("己")
    assert flow_targets != transformation_targets("乙")
    assert flow_targets != transformation_targets("戊")
    assert result.transformations[0].earthly_branch == "寅"
    assert result.transformations[0].earthly_branch != result.flow_life_palace_branch


def test_2026_before_first_major_luck_still_has_four_transformations() -> None:
    result = calculate_flow_year(calculate_basic_chart(case_a()), 2026)
    assert result.ganzhi.display == "丙午"
    assert result.active_major_luck is None
    assert result.before_first_major_luck
    assert tuple(item.star_name.value for item in result.transformations) == TEN_STEM_TABLE["丙"]


def test_2032_ren_science_remains_tianfu_edition_choice() -> None:
    result = calculate_flow_year(calculate_basic_chart(case_a()), 2032)
    assert result.ganzhi.display == "壬子"
    assert tuple(item.star_name.value for item in result.transformations) == (
        "天梁", "紫微", "天府", "武曲",
    )
    assert result.transformations[2].star_name.value == "天府"


def test_2039_gender_changes_major_luck_but_not_flow_transformations() -> None:
    female = calculate_flow_year(calculate_basic_chart(case_a("female")), 2039)
    male = calculate_flow_year(calculate_basic_chart(case_a("male")), 2039)
    assert female.transformations == male.transformations
    assert female.active_major_luck is not None
    assert male.active_major_luck is not None
    assert female.active_major_luck.palace_ganzhi.display == "己卯"
    assert male.active_major_luck.palace_ganzhi.display == "己丑"


def test_targets_exist_once_and_preserve_natal_category_branch_and_palace() -> None:
    chart = calculate_basic_chart(case_a())
    natal = [
        (star.name, star.earthly_branch, "major", palace.palace_name)
        for palace in chart.palaces for star in palace.major_stars
    ] + [
        (star.name, star.earthly_branch, "auxiliary", palace.palace_name)
        for palace in chart.palaces for star in palace.auxiliary_stars
    ]
    before = chart.model_dump(round_trip=True)
    for year in (2026, 2029, 2032, 2039):
        result = calculate_flow_year(chart, year)
        for record in result.transformations:
            matches = [row for row in natal if row[0] == record.star_name]
            assert len(matches) == 1
            _, branch, category, palace = matches[0]
            assert (record.earthly_branch, record.star_category.value, record.natal_palace_name) == (
                branch, category, palace,
            )
    assert chart.model_dump(round_trip=True) == before


def test_missing_or_duplicate_target_is_a_domain_error() -> None:
    target = transformation_targets("己")[0]
    with pytest.raises(ValueError, match="exactly once"):
        _locate_target(target, [])
    with pytest.raises(ValueError, match="exactly once"):
        _locate_target(target, [(target, "寅", "major"), (target, "卯", "major")])


@pytest.mark.parametrize("defect", ("target_year", "target", "type", "category", "branch", "palace"))
def test_flow_year_model_rejects_corrupted_transformation_facts(defect: str) -> None:
    result = calculate_flow_year(calculate_basic_chart(case_a()), 2029)
    payload = result.model_dump(round_trip=True)
    row = payload["transformations"][0]
    if defect == "target_year":
        payload["target_lunar_year"] = 2030
    elif defect == "target":
        row["star_name"] = "天機"
    elif defect == "type":
        row["transformation_type"] = "化權"
    elif defect == "category":
        row["star_category"] = "auxiliary"
    elif defect == "branch":
        row["earthly_branch"] = "卯"
    else:
        row["natal_palace_name"] = "父母宮"
    with pytest.raises(ValidationError):
        FlowYearResult.model_validate(payload)


@pytest.mark.parametrize("solar,lunar", ((SOLAR_A, LUNAR_A), (SOLAR_L, LUNAR_L)))
def test_equivalent_birth_inputs_have_identical_flow_year_transformations(solar, lunar) -> None:
    solar_chart = calculate_basic_chart(normalize_birth_input(BirthInput.model_validate(solar)))
    lunar_chart = calculate_basic_chart(normalize_birth_input(BirthInput.model_validate(lunar)))
    assert calculate_flow_year(solar_chart, 2029).transformations == calculate_flow_year(
        lunar_chart, 2029,
    ).transformations


def test_api_includes_authoritative_transformations_without_nvidia(monkeypatch) -> None:
    calls = 0

    async def forbidden_chat(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("NVIDIA must not run for Flow-Year transformations")

    monkeypatch.setattr(NvidiaClient, "chat", forbidden_chat)
    response = client.post("/api/flow-year", json={"birth_input": SOLAR_A, "target_year": 2029})
    assert response.status_code == 200
    assert len(response.json()["transformations"]) == 4
    assert normalized(FlowYearResult.model_validate(response.json())) == CASE_A_FLOW_YEAR_TRANSFORMATIONS[2029]
    assert calls == 0


def test_ui_distinguishes_birth_major_luck_and_flow_year_transformations() -> None:
    html = client.get("/ziwei").text
    javascript = client.get("/static/ziwei.js").text
    assert "生年四化" in html
    assert "大限四化" in html
    assert 'id="flow-year-transformations-heading">流年四化<' in html
    assert 'id="flow-year-transformation-body"' in html
    assert "payload.transformations.forEach" in javascript
    assert 'document.querySelector("#flow-year-transformation-body").replaceChildren()' in javascript
    assert "innerHTML" not in javascript


def test_phase6d_scope_excludes_moving_stars_and_png_integration() -> None:
    payload = calculate_flow_year(calculate_basic_chart(case_a()), 2029).model_dump_json()
    for forbidden in (
        "流魁", "流鉞", "流昌", "流曲", "流鸞", "流喜", "流祿", "流羊",
        "流陀", "流馬", "年解", "歲建", "博士", "將前", "長生", "interpretation",
    ):
        assert forbidden not in payload
    root = Path(__file__).resolve().parents[1]
    assert "flow_year" not in (root / "app/chart/renderer.py").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def external_flow_year_transformations():
    root = Path(__file__).resolve().parents[1]
    node = shutil.which("node")
    receipt = root / "tmp/phase1f-iztro/build-receipt.json"
    if not node or not receipt.exists():
        pytest.skip("pinned iztro development engine/Node absent")
    process = subprocess.run(
        [node, "tests/verify_iztro_flow_year.cjs"], cwd=root, check=False,
        capture_output=True, text=True, encoding="utf-8", env=os.environ,
    )
    assert process.returncode == 0, process.stderr + process.stdout
    return json.loads(process.stdout)


def test_pinned_iztro_matches_except_known_ren_science_variant(
    external_flow_year_transformations,
) -> None:
    differences = []
    for external in external_flow_year_transformations["results"]:
        result = calculate_flow_year(calculate_basic_chart(case_a()), external["targetYear"])
        assert external["stem"] == result.heavenly_stem
        for transformation, tiger, iztro in zip(
            TYPES,
            (item.star_name.value for item in result.transformations),
            external["targets"],
            strict=True,
        ):
            if tiger != iztro:
                differences.append({
                    "year": external["targetYear"],
                    "stem": external["stem"],
                    "transformation": transformation,
                    "tiger": tiger,
                    "iztro": iztro,
                })
    assert differences == [{
        "year": 2032,
        "stem": "壬",
        "transformation": "化科",
        "tiger": "天府",
        "iztro": "左輔",
    }]


def test_flow_year_transformation_model_is_minimal() -> None:
    assert set(FlowYearTransformation.model_fields) == {
        "transformation_type", "star_name", "star_category", "earthly_branch", "natal_palace_name",
    }
