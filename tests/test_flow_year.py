"""Phase 6C deterministic Flow-Year calculation and API contracts."""

import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from app.birth_input import normalize_birth_input
from app.calendar.ganzhi import calculate_lunar_year_ganzhi
from app.main import app
from app.models.birth import BirthData, BirthInput
from app.models.calendar import EARTHLY_BRANCHES
from app.models.flow_year import FlowYearRequest, FlowYearResult
from app.ziwei.basic_chart import calculate_basic_chart
from app.ziwei.flow_year import calculate_flow_year, flow_year_palace_branches
import app.ziwei.flow_year as flow_year_module
import app.calendar.ganzhi as ganzhi_module

from tests.flow_year_reference import CASE_A_2026, CASE_A_2029


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


def palace_facts(result: FlowYearResult) -> tuple[tuple[str, str, str, str, str], ...]:
    return tuple(
        (
            palace.flow_palace_name.value,
            palace.earthly_branch,
            palace.natal_palace_name.value,
            palace.natal_palace_heavenly_stem,
            palace.natal_palace_ganzhi.display,
        )
        for palace in result.palaces
    )


@pytest.mark.parametrize(
    ("year", "expected"),
    ((2025, "乙巳"), (2026, "丙午"), (2029, "己酉"), (2039, "己未")),
)
def test_static_lunar_year_ganzhi(year: int, expected: str) -> None:
    assert calculate_lunar_year_ganzhi(year).display == expected


def test_flow_year_ganzhi_reuses_phase1b_lunar_conversion_path() -> None:
    source = inspect.getsource(ganzhi_module.calculate_lunar_year_ganzhi)
    assert "to_solar" in source
    assert "_solar_day" in source
    assert "getYearGZ(True)" in source
    assert "LunarDate(year=lunar_year, month=1, day=1" in source


@pytest.mark.parametrize("life_branch", EARTHLY_BRANCHES)
def test_all_twelve_flow_life_branches_rotate_forward(life_branch: str) -> None:
    start = EARTHLY_BRANCHES.index(life_branch)
    expected = tuple(EARTHLY_BRANCHES[(start + offset) % 12] for offset in range(12))
    actual = flow_year_palace_branches(life_branch)
    assert actual == expected
    assert len(actual) == 12
    assert len(set(actual)) == 12


@pytest.mark.parametrize("year,age", ((2025, 1), (2026, 2), (2027, 3), (2028, 4), (2029, 5), (2030, 6)))
def test_nominal_age_uses_only_lunar_years(year: int, age: int) -> None:
    assert calculate_flow_year(calculate_basic_chart(case_a()), year).nominal_age == age


def test_case_a_2029_complete_acceptance_result() -> None:
    result = calculate_flow_year(calculate_basic_chart(case_a()), 2029)
    assert (result.target_lunar_year, result.ganzhi.display) == (2029, "己酉")
    assert (result.nominal_age, result.flow_life_palace_branch) == (5, "酉")
    assert palace_facts(result) == CASE_A_2029
    assert result.active_major_luck is not None
    assert (
        result.active_major_luck.start_nominal_age,
        result.active_major_luck.end_nominal_age,
        result.active_major_luck.palace_ganzhi.display,
        result.active_major_luck.palace_name.value,
    ) == (5, 14, "戊寅", "命宮")
    assert not result.before_first_major_luck
    assert not result.after_supported_major_luck


def test_case_a_2026_is_complete_and_before_first_major_luck() -> None:
    result = calculate_flow_year(calculate_basic_chart(case_a()), 2026)
    assert (result.ganzhi.display, result.nominal_age, result.flow_life_palace_branch) == ("丙午", 2, "午")
    assert palace_facts(result) == CASE_A_2026
    assert result.active_major_luck is None
    assert result.before_first_major_luck
    assert not result.after_supported_major_luck


def test_2039_gender_changes_only_active_major_luck() -> None:
    female = calculate_flow_year(calculate_basic_chart(case_a("female")), 2039)
    male = calculate_flow_year(calculate_basic_chart(case_a("male")), 2039)
    assert (female.ganzhi.display, female.nominal_age, female.flow_life_palace_branch) == ("己未", 15, "未")
    assert female.palaces == male.palaces
    assert female.active_major_luck is not None
    assert male.active_major_luck is not None
    assert (
        female.active_major_luck.start_nominal_age,
        female.active_major_luck.end_nominal_age,
        female.active_major_luck.palace_ganzhi.display,
        female.active_major_luck.palace_name.value,
    ) == (15, 24, "己卯", "父母宮")
    assert (
        male.active_major_luck.start_nominal_age,
        male.active_major_luck.end_nominal_age,
        male.active_major_luck.palace_ganzhi.display,
        male.active_major_luck.palace_name.value,
    ) == (15, 24, "己丑", "兄弟宮")


def test_2029_gender_does_not_change_first_major_luck_or_flow_year_core() -> None:
    female = calculate_flow_year(calculate_basic_chart(case_a("female")), 2029)
    male = calculate_flow_year(calculate_basic_chart(case_a("male")), 2029)
    assert female.palaces == male.palaces
    assert female.ganzhi == male.ganzhi
    assert female.nominal_age == male.nominal_age
    assert female.active_major_luck == male.active_major_luck


@pytest.mark.parametrize("solar,lunar", ((SOLAR_A, LUNAR_A), (SOLAR_L, LUNAR_L)))
def test_equivalent_solar_and_lunar_birth_inputs_have_identical_flow_year(solar, lunar) -> None:
    solar_chart = calculate_basic_chart(normalize_birth_input(BirthInput.model_validate(solar)))
    lunar_chart = calculate_basic_chart(normalize_birth_input(BirthInput.model_validate(lunar)))
    assert calculate_flow_year(solar_chart, 2029) == calculate_flow_year(lunar_chart, 2029)


def test_flow_year_reuses_exact_natal_palace_hosts_and_ganzhi() -> None:
    chart = calculate_basic_chart(case_a())
    result = calculate_flow_year(chart, 2029)
    hosts = {palace.earthly_branch: palace for palace in chart.palaces}
    for palace in result.palaces:
        host = hosts[palace.earthly_branch]
        assert palace.natal_palace_name is host.palace_name
        assert palace.natal_palace_heavenly_stem == host.heavenly_stem
        assert palace.natal_palace_ganzhi == host.palace_ganzhi


def test_after_last_major_luck_is_explicit() -> None:
    result = calculate_flow_year(calculate_basic_chart(case_a()), 2149)
    assert result.nominal_age == 125
    assert result.active_major_luck is None
    assert not result.before_first_major_luck
    assert result.after_supported_major_luck


def test_prebirth_target_year_is_rejected() -> None:
    with pytest.raises(ValueError, match="earlier than the birth lunar year"):
        calculate_flow_year(calculate_basic_chart(case_a()), 2024)
    response = client.post("/api/flow-year", json={"birth_input": SOLAR_A, "target_year": 2024})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_FLOW_YEAR"


@pytest.mark.parametrize("value", (2029.0, "2029", None, True, 1582, 10000))
def test_request_rejects_non_strict_or_unsupported_target_year(value) -> None:
    with pytest.raises(ValidationError):
        FlowYearRequest.model_validate({"birth_input": SOLAR_A, "target_year": value})
    assert client.post("/api/flow-year", json={"birth_input": SOLAR_A, "target_year": value}).status_code == 422


def test_explicit_target_year_is_required() -> None:
    with pytest.raises(ValidationError):
        FlowYearRequest.model_validate({"birth_input": SOLAR_A})
    assert client.post("/api/flow-year", json={"birth_input": SOLAR_A}).status_code == 422


def test_api_rebuilds_authoritative_chart_and_returns_complete_result(monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("NVIDIA/interpreter must not run for Flow-Year")

    monkeypatch.setattr("app.llm.interpreter.ZiweiInterpreter.interpret", forbidden)
    response = client.post("/api/flow-year", json={"birth_input": SOLAR_A, "target_year": 2029})
    assert response.status_code == 200
    result = FlowYearResult.model_validate(response.json())
    assert palace_facts(result) == CASE_A_2029


def test_flow_year_has_no_system_date_or_out_of_scope_fields() -> None:
    source = inspect.getsource(flow_year_module).lower()
    for forbidden in ("date.today", "datetime.now", "date.now"):
        assert forbidden not in source
    assert set(FlowYearResult.model_fields) == {
        "target_lunar_year", "heavenly_stem", "earthly_branch", "ganzhi",
        "nominal_age", "flow_life_palace_branch", "palaces", "transformations", "active_major_luck",
        "before_first_major_luck", "after_supported_major_luck",
    }
    serialized = json.dumps(
        calculate_flow_year(calculate_basic_chart(case_a()), 2029).model_dump(mode="json"),
        ensure_ascii=False,
    )
    for forbidden in ("流魁", "流鉞", "流昌", "流曲", "流鸞", "流喜", "流祿", "流羊", "流陀", "流馬", "年解", "童限", "小限", "interpretation"):
        assert forbidden not in serialized


def test_flow_year_model_rejects_tampered_rotation() -> None:
    result = calculate_flow_year(calculate_basic_chart(case_a()), 2029)
    payload = result.model_dump(round_trip=True)
    payload["palaces"][0]["earthly_branch"] = "申"
    with pytest.raises(ValidationError):
        FlowYearResult.model_validate(payload)


def test_openapi_and_ui_expose_explicit_flow_year_workflow() -> None:
    schema = client.get("/openapi.json").json()
    assert "post" in schema["paths"]["/api/flow-year"]
    html = client.get("/ziwei").text
    javascript = client.get("/static/ziwei.js").text
    for expected in (
        'id="target-solar-year" type="number"',
        'id="target-solar-month" type="number"',
        'id="target-solar-day" type="number"',
        'id="target-lunar-year" type="number"',
        'id="target-lunar-month" type="number"',
        'id="target-lunar-day" type="number"',
        'id="flow-date-button" type="button" class="primary" disabled',
        'id="flow-year-summary"',
        'id="flow-year-body"',
        "系統會轉換為農曆後計算",
        "尚未進入第一大限",
        "流年年份",
        "目前大限",
        "所落本命宮",
    ):
        assert expected in html + javascript
    assert javascript.count('fetch("/api/flow-query"') == 1
    assert javascript.count('fetch("/api/flow-year"') == 0
    assert 'flowYearButton.addEventListener("click"' in javascript
    assert "flowQueryInputs.forEach" in javascript
    assert "invalidateFlowYear();" in javascript[javascript.index('form.addEventListener("input"'):]
    assert "new Date" not in javascript
    assert "Date.now" not in javascript
    assert "innerHTML" not in javascript
    for forbidden in ("流魁", "流鉞", "流昌", "流曲", "流鸞", "流喜", "流祿", "流羊", "流陀", "流馬", "小限", "童限"):
        assert forbidden not in html


@pytest.fixture(scope="module")
def external_flow_year_report():
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


@pytest.mark.parametrize("index", range(4))
def test_pinned_iztro_flow_year_comparison(external_flow_year_report, index: int) -> None:
    external = external_flow_year_report["results"][index]
    result = calculate_flow_year(calculate_basic_chart(case_a()), external["targetYear"])
    assert (external["stem"], external["branch"]) == (
        result.heavenly_stem, result.earthly_branch,
    )
    life = next(item for item in external["palaces"] if item["flowPalace"] == "命宮")
    assert life["branch"] == result.flow_life_palace_branch
    external_by_branch = {item["branch"]: item["flowPalace"] for item in external["palaces"]}
    assert external_by_branch == {
        item.earthly_branch: item.flow_palace_name.value for item in result.palaces
    }
