"""Gregorian/lunar input normalization and integration tests."""

from datetime import date

from fastapi.testclient import TestClient

import app.api.chart as chart_api
from app.birth_input import normalize_birth_input
from app.calendar.lunar import to_lunar, to_solar
from app.llm.interpreter import serialize_chart_facts
from app.main import app
from app.models.birth import BirthInput
from app.models.calendar import LunarDate
from app.models.interpretation import InterpretationResult
from app.models.ziwei import PalaceName


client = TestClient(app)

COMMON = {
    "name": "相同出生資料",
    "gender": "female",
    "birth_hour": 0,
    "birth_minute": 30,
    "birthplace": "Taipei",
}
SOLAR_A = COMMON | {
    "calendar_type": "solar",
    "birth_year": 2025,
    "birth_month": 1,
    "birth_day": 29,
}
LUNAR_A = COMMON | {
    "calendar_type": "lunar",
    "lunar_year": 2025,
    "lunar_month": 1,
    "lunar_day": 1,
    "is_leap_month": False,
}
SOLAR_L = COMMON | {
    "calendar_type": "solar",
    "birth_year": 2025,
    "birth_month": 7,
    "birth_day": 25,
    "birth_hour": 12,
    "birth_minute": 0,
}
LUNAR_L = COMMON | {
    "calendar_type": "lunar",
    "lunar_year": 2025,
    "lunar_month": 6,
    "lunar_day": 1,
    "is_leap_month": True,
    "birth_hour": 12,
    "birth_minute": 0,
}


def interpretation_result() -> InterpretationResult:
    return InterpretationResult.model_validate(
        {
            "overview": "命盤總覽。",
            "palace_interpretations": [
                {"palace_name": palace.value, "summary": f"{palace.value}解讀。"}
                for palace in PalaceName
            ],
            "transformation_analysis": "生年四化解讀。",
            "overall": {
                "personality": "性格。",
                "career": "職涯。",
                "finance": "財務。",
                "relationships": "感情。",
                "interpersonal": "人際。",
                "family": "家庭。",
                "strengths": "優勢。",
                "potential_challenges": "挑戰。",
            },
        }
    )


def test_explicit_gregorian_mode_preserves_existing_chart() -> None:
    explicit = client.post("/api/chart", json=SOLAR_A)
    legacy = client.post(
        "/api/chart",
        json={key: value for key, value in SOLAR_A.items() if key != "calendar_type"},
    )
    assert explicit.status_code == legacy.status_code == 200
    assert explicit.json() == legacy.json()


def test_normal_lunar_case_a_converts_and_matches_gregorian_chart() -> None:
    normalized = normalize_birth_input(BirthInput.model_validate(LUNAR_A))
    assert (normalized.birth_year, normalized.birth_month, normalized.birth_day) == (2025, 1, 29)
    lunar_chart = client.post("/api/chart", json=LUNAR_A)
    solar_chart = client.post("/api/chart", json=SOLAR_A)
    assert lunar_chart.status_code == solar_chart.status_code == 200
    assert lunar_chart.json() == solar_chart.json()


def test_leap_lunar_case_l_converts_and_matches_complete_gregorian_chart() -> None:
    normalized = normalize_birth_input(BirthInput.model_validate(LUNAR_L))
    assert (normalized.birth_year, normalized.birth_month, normalized.birth_day) == (2025, 7, 25)
    lunar = client.post("/api/chart", json=LUNAR_L)
    solar = client.post("/api/chart", json=SOLAR_L)
    assert lunar.status_code == solar.status_code == 200
    assert lunar.json() == solar.json()

    chart = lunar.json()
    assert chart["life_palace_branch"] == "寅"
    assert chart["body_palace_branch"] == "寅"
    assert chart["five_elements_bureau"]["bureau_name"] == "土五局"
    major = {star["name"]: star["earthly_branch"] for star in chart["major_star_chart"]["stars"]}
    auxiliary = {star["name"]: star["earthly_branch"] for star in chart["auxiliary_star_chart"]["stars"]}
    assert auxiliary["左輔"] == "戌"
    assert auxiliary["右弼"] == "辰"
    assert major["紫微"] == "午"
    assert major["天府"] == "戌"


def test_lunar_and_solar_modes_preserve_all_star_and_transformation_results() -> None:
    solar = client.post("/api/chart", json=SOLAR_L).json()
    lunar = client.post("/api/chart", json=LUNAR_L).json()
    for field in ("major_star_chart", "auxiliary_star_chart", "birth_year_transformations", "palaces"):
        assert lunar[field] == solar[field]


def test_impossible_lunar_date_is_rejected_clearly() -> None:
    response = client.post(
        "/api/chart",
        json=LUNAR_A | {"lunar_month": 2, "lunar_day": 30},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "INVALID_BIRTH_DATE",
        "message": "指定的農曆日期不存在。",
    }


def test_invalid_leap_month_selection_is_not_silently_treated_as_ordinary() -> None:
    response = client.post(
        "/api/chart",
        json=LUNAR_A | {"lunar_month": 5, "is_leap_month": True},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "INVALID_BIRTH_DATE",
        "message": "指定的農曆年份沒有該閏月。",
    }


def test_static_round_trip_invariants_include_leap_month() -> None:
    solar_cases = (
        date(2025, 1, 29),
        date(2024, 2, 29),
        date(2025, 7, 24),
        date(2025, 7, 25),
    )
    for solar in solar_cases:
        assert to_solar(to_lunar(solar)) == solar

    lunar_cases = (
        LunarDate(year=2025, month=1, day=1, is_leap_month=False),
        LunarDate(year=2025, month=6, day=30, is_leap_month=False),
        LunarDate(year=2025, month=6, day=1, is_leap_month=True),
    )
    for lunar in lunar_cases:
        assert to_lunar(to_solar(lunar)) == lunar


def test_png_is_identical_for_same_moment_entered_in_either_mode() -> None:
    solar = client.post("/api/chart/png", json=SOLAR_L)
    lunar = client.post("/api/chart/png", json=LUNAR_L)
    assert solar.status_code == lunar.status_code == 200
    assert solar.headers["content-type"] == lunar.headers["content-type"] == "image/png"
    assert solar.content == lunar.content


def test_interpretation_receives_identical_authoritative_chart_facts(monkeypatch) -> None:
    facts = []

    class FakeInterpreter:
        async def interpret(self, chart):
            facts.append(serialize_chart_facts(chart))
            return interpretation_result()

    monkeypatch.setattr(chart_api, "ZiweiInterpreter", FakeInterpreter)
    solar = client.post("/api/interpret", json=SOLAR_L)
    lunar = client.post("/api/interpret", json=LUNAR_L)
    assert solar.status_code == lunar.status_code == 200
    assert solar.json() == lunar.json()
    assert len(facts) == 2
    assert facts[0] == facts[1]


def test_ui_has_calendar_selector_and_mode_specific_fields() -> None:
    html = client.get("/ziwei").text
    assert 'name="calendar_type"' in html
    assert 'value="solar" checked' in html
    assert 'value="lunar"' in html
    for field in ("lunar_year", "lunar_month", "lunar_day", "is_leap_month"):
        assert f'id="{field}"' in html
    assert "日期類型" in html
    assert "國曆" in html
    assert "農曆" in html


def test_ui_switches_inputs_and_displays_both_calendar_dates() -> None:
    javascript = client.get("/static/ziwei.js").text
    assert "function updateCalendarMode()" in javascript
    assert "field.hidden = lunarMode" in javascript
    assert "field.hidden = !lunarMode" in javascript
    calendar_mode = javascript[javascript.index("function updateCalendarMode"):javascript.index("function setNumericValuesShown")]
    assert "birthDateTimeShown" not in calendar_mode
    assert 'calendarType === "lunar"' in javascript
    assert 'addSummary("輸入方式"' in javascript
    assert 'addSummary("西元日期"' in javascript
    assert 'addSummary("農曆日期"' in javascript
    assert '"換算國曆"' in javascript
