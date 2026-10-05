"""HTTP contract tests for the minimal Phase 2B browser UI."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
PRESET_A = {
    "name": "預設 A", "gender": "female", "birth_year": 2025,
    "birth_month": 1, "birth_day": 29, "birth_hour": 0,
    "birth_minute": 30, "birthplace": "Taipei",
}


def post_chart(**overrides: object):
    return client.post("/api/chart", json=PRESET_A | overrides)


def test_ziwei_page_is_available() -> None:
    response = client.get("/ziwei")
    assert response.status_code == 200
    assert "紫微斗數排盤" in response.text


def test_page_has_all_required_inputs() -> None:
    html = client.get("/ziwei").text
    for input_id in ("name", "gender", "birth_year", "birth_month", "birth_day", "birth_hour", "birth_minute", "birthplace"):
        assert f'id="{input_id}"' in html
    assert "排盤" in html


def test_page_has_standard_time_notice() -> None:
    assert "目前使用輸入的民用／標準時間。真太陽時尚未實作。" in client.get("/ziwei").text


def test_page_has_all_five_presets() -> None:
    html = client.get("/ziwei").text
    for key in "ABCLZ":
        assert f'data-preset="{key}"' in html


def test_page_documents_deterministic_rules() -> None:
    html = client.get("/ziwei").text
    for expected in ("農曆正月初一", "晚子時：23:xx 不換日", "整個閏月按次月處理本命月規則", "天梁化祿、紫微化權、天府化科、武曲化忌", "LLM 不參與排盤"):
        assert expected in html


def test_static_assets_are_available() -> None:
    assert client.get("/static/ziwei.css").status_code == 200
    assert client.get("/static/ziwei.js").status_code == 200


def test_chart_endpoint_returns_integrated_result() -> None:
    response = post_chart()
    assert response.status_code == 200
    result = response.json()
    assert result["birth_data"] == PRESET_A
    assert len(result["palaces"]) == 12
    assert len(result["birth_year_transformations"]["transformations"]) == 4


def test_preset_a_calendar_result_is_unchanged() -> None:
    result = post_chart().json()
    assert result["calendar"]["lunar_date"] == {"year": 2025, "month": 1, "day": 1, "is_leap_month": False}
    assert result["calendar"]["year_ganzhi"] == {"heavenly_stem": "乙", "earthly_branch": "巳"}


def test_preset_a_palace_result_is_unchanged() -> None:
    result = post_chart().json()
    assert result["life_palace_branch"] == "寅"
    assert result["body_palace_branch"] == "寅"
    assert result["body_palace_name"] == "命宮"
    assert result["five_elements_bureau"]["bureau_name"] == "土五局"


def test_preset_a_star_counts_are_unchanged() -> None:
    palaces = post_chart().json()["palaces"]
    assert sum(len(palace["major_stars"]) for palace in palaces) == 14
    assert sum(len(palace["auxiliary_stars"]) for palace in palaces) == 14


def test_preset_a_transformations_are_unchanged() -> None:
    result = post_chart().json()["birth_year_transformations"]
    assert result["year_heavenly_stem"] == "乙"
    assert [item["transformation"] for item in result["transformations"]] == ["化祿", "化權", "化科", "化忌"]
    assert [item["star_name"] for item in result["transformations"]] == ["天機", "天梁", "紫微", "太陰"]


def test_leap_month_preset_uses_next_effective_month() -> None:
    result = post_chart(name="預設 L", gender="female", birth_year=2025, birth_month=7, birth_day=25, birth_hour=12, birth_minute=0, birthplace="Taipei").json()
    assert result["calendar"]["lunar_date"] == {"year": 2025, "month": 6, "day": 1, "is_leap_month": True}
    assert result["palace_layout"]["effective_lunar_month"] == 7


def test_leap_boundary_left_side_is_not_leap_month() -> None:
    result = post_chart(birth_year=2025, birth_month=7, birth_day=24).json()
    assert result["calendar"]["lunar_date"]["is_leap_month"] is False
    assert result["palace_layout"]["effective_lunar_month"] == 6


def test_leap_boundary_right_side_remains_leap_month() -> None:
    result = post_chart(birth_year=2025, birth_month=8, birth_day=22).json()
    assert result["calendar"]["lunar_date"]["is_leap_month"] is True
    assert result["palace_layout"]["effective_lunar_month"] == 7


def test_leap_month_preset_retains_adopted_month_stars() -> None:
    result = post_chart(name="預設 L", birth_year=2025, birth_month=7, birth_day=25, birth_hour=12, birth_minute=0).json()
    stars = result["auxiliary_star_chart"]["stars"]
    star_to_branch = {star["name"]: star["earthly_branch"] for star in stars}
    assert star_to_branch["左輔"] == "戌"
    assert star_to_branch["右弼"] == "辰"


def test_late_zi_preset_keeps_same_civil_day() -> None:
    result = post_chart(name="預設 Z", birth_year=2025, birth_month=7, birth_day=24, birth_hour=23, birth_minute=59, birthplace="Taipei").json()
    assert result["calendar"]["solar_date"] == "2025-07-24"
    assert result["calendar"]["lunar_date"] == {"year": 2025, "month": 6, "day": 30, "is_leap_month": False}
    assert result["calendar"]["hour_ganzhi"]["earthly_branch"] == "子"


def test_invalid_gregorian_date_is_rejected() -> None:
    assert post_chart(birth_year=2025, birth_month=2, birth_day=30).status_code == 422


def test_invalid_hour_is_rejected() -> None:
    assert post_chart(birth_hour=24).status_code == 422


def test_blank_birthplace_is_rejected() -> None:
    assert post_chart(birthplace="   ").status_code == 422


def test_missing_birthplace_is_rejected() -> None:
    payload = PRESET_A.copy()
    payload.pop("birthplace")
    assert client.post("/api/chart", json=payload).status_code == 422


def test_unsupported_gender_is_rejected() -> None:
    assert post_chart(gender="other").status_code == 422


def test_invalid_minute_is_rejected() -> None:
    assert post_chart(birth_minute=60).status_code == 422


def test_unknown_request_fields_are_rejected() -> None:
    assert post_chart(unsupported_rule="value").status_code == 422


def test_frontend_contains_no_astrology_rule_tables() -> None:
    javascript = client.get("/static/ziwei.js").text
    assert "BIRTH_YEAR_TRANSFORMATION" not in javascript
    assert "MAJOR_STAR" not in javascript
    assert "AUXILIARY_STAR" not in javascript


def test_frontend_calls_only_local_chart_endpoint() -> None:
    javascript = client.get("/static/ziwei.js").text
    assert 'fetch("/api/chart"' in javascript
    assert "http://" not in javascript
    assert "https://" not in javascript


def test_openapi_exposes_chart_endpoint() -> None:
    schema = client.get("/openapi.json").json()
    assert "post" in schema["paths"]["/api/chart"]
