"""Phase 8B-R5 Gregorian/lunar hierarchical Flow-Query contracts."""

from datetime import date

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from app.api.chart import _calculate_input_chart
from app.calendar.ganzhi import calculate_lunar_month_ganzhi
from app.main import app
from app.models.birth import BirthInput
from app.models.flow_query import FlowQueryRequest, LunarFlowQueryInput, SolarFlowQueryInput
from app.ziwei.flow_query import calculate_flow_query, normalize_flow_target


client = TestClient(app)
SOLAR_A = {
    "name": "Case A", "gender": "female", "calendar_type": "solar",
    "birth_year": 2025, "birth_month": 1, "birth_day": 29,
    "birth_hour": 0, "birth_minute": 30, "birthplace": "Taipei",
}
SOLAR_L = {
    "name": "Case L", "gender": "female", "calendar_type": "solar",
    "birth_year": 2025, "birth_month": 7, "birth_day": 25,
    "birth_hour": 12, "birth_minute": 0, "birthplace": "Taipei",
}


def chart(payload: dict = SOLAR_A):
    return _calculate_input_chart(BirthInput.model_validate(payload))


def test_gregorian_full_date_normalizes_and_calculates_all_layers_without_nvidia(monkeypatch) -> None:
    async def forbidden(*args, **kwargs):
        raise AssertionError("Flow-Query must never call NVIDIA")

    monkeypatch.setattr("app.llm.nvidia_client.NvidiaClient.chat", forbidden)
    response = client.post(
        "/api/flow-query",
        json={
            "birth_input": SOLAR_A,
            "query": {"mode": "solar", "year": 2029, "month": 2, "day": 13},
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["query_mode"] == "solar"
    assert result["normalized_target"] == {
        "input_mode": "solar",
        "original_solar_date": "2029-02-13",
        "original_lunar_year": None,
        "original_lunar_month": None,
        "original_lunar_day": None,
        "original_is_leap_month": None,
        "converted_solar_date": None,
        "lunar_year": 2029,
        "lunar_month": 1,
        "lunar_day": 1,
        "is_leap_month": False,
        "effective_month": 1,
    }
    assert "".join(result["flow_year"]["ganzhi"].values()) == "己酉"
    assert "".join(result["flow_month"]["month_ganzhi"].values()) == "丙寅"
    assert result["flow_month"]["flow_month_life_palace_branch"] == "酉"
    assert "".join(result["flow_day"]["day_ganzhi"].values()) == "甲戌"
    assert result["flow_day"]["flow_day_life_palace_branch"] == "酉"


@pytest.mark.parametrize(
    "query",
    (
        {"mode": "solar", "year": 2029},
        {"mode": "solar", "year": 2029, "month": 2},
        {"mode": "solar", "year": 2029, "month": 2, "day": 30},
    ),
)
def test_gregorian_partial_or_invalid_date_is_rejected(query: dict) -> None:
    response = client.post("/api/flow-query", json={"birth_input": SOLAR_A, "query": query})
    assert response.status_code == 422


def test_lunar_year_month_and_day_granularity() -> None:
    natal = chart()
    year = calculate_flow_query(natal, LunarFlowQueryInput(year=2026))
    month = calculate_flow_query(natal, LunarFlowQueryInput(year=2026, month=10))
    day = calculate_flow_query(natal, LunarFlowQueryInput(year=2026, month=10, day=7))
    assert year.flow_year is not None and year.flow_month is None and year.flow_day is None
    assert month.flow_year is not None and month.flow_month is not None and month.flow_day is None
    assert day.flow_year is not None and day.flow_month is not None and day.flow_day is not None
    assert month.flow_month.month_ganzhi == calculate_lunar_month_ganzhi(2026, 10)


@pytest.mark.parametrize(
    "query",
    (
        {"mode": "lunar", "month": 10},
        {"mode": "lunar", "year": 2026, "day": 7},
        {"mode": "lunar", "year": 2026, "is_leap_month": True},
        {"mode": "lunar", "year": 2026, "month": 6, "is_leap_month": True},
    ),
)
def test_invalid_lunar_hierarchy_or_leap_month_is_rejected(query: dict) -> None:
    with pytest.raises(ValidationError):
        FlowQueryRequest.model_validate({"birth_input": SOLAR_A, "query": query})


def test_verified_lunar_leap_month_is_supported() -> None:
    query = LunarFlowQueryInput(year=2025, month=6, is_leap_month=True)
    target = normalize_flow_target(query)
    assert (target.lunar_year, target.lunar_month, target.is_leap_month, target.effective_month) == (
        2025, 6, True, 7,
    )


def test_lunar_new_year_boundary_changes_normalized_flow_year_not_gregorian_year() -> None:
    before = normalize_flow_target(SolarFlowQueryInput(year=2029, month=2, day=12))
    new_year = normalize_flow_target(SolarFlowQueryInput(year=2029, month=2, day=13))
    assert before.original_solar_date == date(2029, 2, 12)
    assert new_year.original_solar_date == date(2029, 2, 13)
    assert (before.lunar_year, before.lunar_month, before.lunar_day) == (2028, 12, 29)
    assert (new_year.lunar_year, new_year.lunar_month, new_year.lunar_day) == (2029, 1, 1)
    assert calculate_flow_query(chart(), SolarFlowQueryInput(year=2029, month=2, day=12)).flow_year.target_lunar_year == 2028
    assert calculate_flow_query(chart(), SolarFlowQueryInput(year=2029, month=2, day=13)).flow_year.target_lunar_year == 2029


def test_equivalent_gregorian_and_lunar_full_dates_have_identical_layers() -> None:
    natal = chart()
    solar = calculate_flow_query(natal, SolarFlowQueryInput(year=2029, month=2, day=13))
    lunar = calculate_flow_query(natal, LunarFlowQueryInput(year=2029, month=1, day=1))
    assert solar.normalized_target.lunar_year == lunar.normalized_target.lunar_year
    assert solar.normalized_target.lunar_month == lunar.normalized_target.lunar_month
    assert solar.normalized_target.lunar_day == lunar.normalized_target.lunar_day
    assert solar.flow_year == lunar.flow_year
    assert solar.flow_month == lunar.flow_month
    assert solar.flow_day == lunar.flow_day


def test_case_l_gregorian_and_leap_lunar_queries_are_equivalent() -> None:
    natal = chart(SOLAR_L)
    solar = calculate_flow_query(natal, SolarFlowQueryInput(year=2025, month=7, day=25))
    lunar = calculate_flow_query(
        natal,
        LunarFlowQueryInput(year=2025, month=6, day=1, is_leap_month=True),
    )
    assert solar.normalized_target.lunar_year == lunar.normalized_target.lunar_year == 2025
    assert solar.normalized_target.lunar_month == lunar.normalized_target.lunar_month == 6
    assert solar.normalized_target.is_leap_month and lunar.normalized_target.is_leap_month
    assert solar.normalized_target.effective_month == lunar.normalized_target.effective_month == 7
    assert solar.flow_year == lunar.flow_year
    assert solar.flow_month == lunar.flow_month
    assert solar.flow_day == lunar.flow_day


def test_flow_query_openapi_and_ui_contract() -> None:
    schema = client.get("/openapi.json").json()
    assert "post" in schema["paths"]["/api/flow-query"]
    html = client.get("/ziwei").text
    javascript = client.get("/static/ziwei.js").text
    for expected in (
        "運限查詢", "查詢日期類型", 'value="solar" checked', 'value="lunar"',
        'id="target-solar-year"', 'id="target-solar-month"', 'id="target-solar-day"',
        'id="target-lunar-year"', 'id="target-lunar-month"', 'id="target-lunar-day"',
        'id="target-is-leap-month"',
    ):
        assert expected in html
    for forbidden in ('id="target-hour"', 'id="target-minute"', 'type="password" min="1583"'):
        assert forbidden not in html
    mode_listener = javascript[
        javascript.index("flowQueryModeInputs.forEach"):
        javascript.index("majorLuckSelect.addEventListener")
    ]
    assert "updateFlowQueryMode();" in mode_listener
    assert "invalidateFlowYear();" in mode_listener
    assert "fetch(" not in mode_listener
    assert 'id="flow-month-section"' in html and 'id="flow-day-section"' in html
    assert "if (payload.flow_month)" in javascript
    assert "if (payload.flow_day)" in javascript
    assert "currentFlowYearTarget = payload.target_lunar_year" in javascript
    assert "request.flow_query = { ...currentFlowQueryInput }" in javascript
    assert javascript.count('fetch("/api/flow-query"') == 1
    assert 'fetch("/api/flow-date"' not in javascript
