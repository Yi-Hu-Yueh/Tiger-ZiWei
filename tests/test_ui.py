"""HTTP contract tests for the minimal Phase 2B browser UI."""

import app.api.chart as chart_api
from fastapi.testclient import TestClient
import pytest

from app.llm.interpreter import InterpretationParseError
from app.llm.nvidia_client import NvidiaClientError, NvidiaErrorCode
from app.main import app
from app.models.interpretation import InterpretationResult
from app.models.ziwei import PalaceName


client = TestClient(app)
PRESET_A = {
    "name": "預設 A", "gender": "female", "birth_year": 2025,
    "birth_month": 1, "birth_day": 29, "birth_hour": 0,
    "birth_minute": 30, "birthplace": "Taipei",
}


def post_chart(**overrides: object):
    return client.post("/api/chart", json=PRESET_A | overrides)


def interpretation_payload() -> dict[str, object]:
    return {
        "overview": "從傳統紫微斗數的角度，此命盤可作為自我觀察參考。",
        "palace_interpretations": [
            {"palace_name": palace.value, "summary": f"{palace.value}解讀。"}
            for palace in PalaceName
        ],
        "transformation_analysis": "依既定生年四化解讀。",
        "overall": {
            "personality": "性格解讀。",
            "career": "職涯解讀。",
            "finance": "財務傾向解讀。",
            "relationships": "感情解讀。",
            "interpersonal": "人際解讀。",
            "family": "家庭解讀。",
            "strengths": "優勢解讀。",
            "potential_challenges": "可留意的挑戰。",
        },
    }


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


def test_birth_datetime_toggle_defaults_to_masked_visible_solar_fields() -> None:
    html = client.get("/ziwei").text
    assert 'id="birth-date-time-toggle" type="button" class="secondary" aria-pressed="false"' in html
    assert "顯示出生年月日時分" in html
    assert '<label class="solar-date-field">西元年' in html
    assert '<label class="solar-date-field">國曆月' in html
    assert '<label class="solar-date-field">國曆日' in html
    assert '<label class="birth-time-field">時' in html
    assert '<label class="birth-time-field">分' in html
    assert '<label class="lunar-date-field" hidden>農曆年' in html
    assert '<label class="lunar-date-field" hidden>是否閏月' in html
    for field in (
        "birth_year", "birth_month", "birth_day", "lunar_year", "lunar_month",
        "lunar_day", "birth_hour", "birth_minute",
    ):
        assert f'id="{field}"' in html
        input_markup = html[html.index(f'id="{field}"'):]
        assert 'type="password"' in input_markup[:250]
        assert 'inputmode="numeric"' in input_markup[:250]
    assert 'id="is_leap_month" name="is_leap_month"' in html


def test_birth_datetime_toggle_masks_only_numeric_values_and_preserves_values() -> None:
    javascript = client.get("/static/ziwei.js").text
    masker = javascript[javascript.index("function setNumericValuesShown"):javascript.index("function setBirthDateTimeShown")]
    setter = javascript[javascript.index("function setBirthDateTimeShown"):javascript.index("function collectInput")]
    assert 'input.type = shown ? "number" : "password"' in masker
    assert "birthDateTimeShown = shown" in setter
    assert 'setAttribute("aria-pressed", String(shown))' in setter
    assert 'shown ? "隱藏出生年月日時分" : "顯示出生年月日時分"' in setter
    assert "setNumericValuesShown(birthDateTimeInputs, shown)" in setter
    for forbidden in (".value =", "fetch(", "invalidate", "clearInterpretation", "clearFlowYear"):
        assert forbidden not in masker + setter

    html = client.get("/ziwei").text
    for still_visible in (
        'id="calendar-solar"', 'id="calendar-lunar"', 'id="name"', 'id="gender"',
        'id="birthplace"', 'id="submit-button"', 'data-preset="A"', 'data-preset="Z"',
    ):
        assert still_visible in html


def test_birth_toggle_preserves_mode_and_preset_without_target_masking() -> None:
    javascript = client.get("/static/ziwei.js").text
    birth_handler = javascript[
        javascript.index('birthDateTimeToggle.addEventListener("click"'):
        javascript.index('form.addEventListener("input"')
    ]
    assert "setBirthDateTimeShown(!birthDateTimeShown)" in birth_handler
    assert "fetch(" not in birth_handler
    assert "invalidate" not in birth_handler
    preset = javascript[javascript.index("function setPreset"):javascript.index("function selectedCalendarType")]
    assert "control.value = value" in preset
    assert "birthDateTimeShown =" not in preset
    calendar_mode = javascript[javascript.index("function updateCalendarMode"):javascript.index("function setNumericValuesShown")]
    assert "lunarMode" in calendar_mode
    assert ".solar-date-field" in calendar_mode
    assert ".lunar-date-field" in calendar_mode
    assert "birthDateTimeShown" not in calendar_mode
    assert ".birth-time-field" not in calendar_mode

    html = client.get("/ziwei").text
    assert "顯示出生年月日時分" in html
    assert "隱藏出生年月日時分" in javascript
    assert "運限年月日時分" not in html + javascript


def test_birth_input_editing_still_invalidates_derived_state() -> None:
    javascript = client.get("/static/ziwei.js").text
    listener = javascript[javascript.index('form.addEventListener("input"'):]
    listener = listener[:listener.index("});") + 3]
    assert "invalidateInterpretation();" in listener


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
    assert len(result["major_luck"]["periods"]) == 12


def test_phase6a_ui_has_major_luck_summary_and_table() -> None:
    html = client.get("/ziwei").text
    javascript = client.get("/static/ziwei.js").text
    assert 'id="major-luck-heading">大限<' in html
    assert 'id="major-luck-summary"' in html
    assert 'id="major-luck-body"' in html
    for heading in ("大限", "歲數", "地支", "宮位", "宮干支", "大限四化"):
        assert f"<th>{heading}</th>" in html
    for text in ("大限方向", "陰陽性別", "歲起限", "start_nominal_age", "end_nominal_age"):
        assert text in javascript
    assert "innerHTML" not in javascript


def test_phase6b_ui_renders_four_transformations_for_every_major_luck_row() -> None:
    javascript = client.get("/static/ziwei.js").text
    assert "period_transformations" in javascript
    assert "major_luck_index" in javascript
    assert "transformation_type" in javascript
    assert "star_name" in javascript
    result = post_chart().json()["major_luck"]
    assert len(result["period_transformations"]) == 12
    assert sum(len(group["transformations"]) for group in result["period_transformations"]) == 48
    first = result["period_transformations"][0]
    assert first["major_luck_heavenly_stem"] == "戊"
    assert [
        (row["transformation_type"], row["star_name"])
        for row in first["transformations"]
    ] == [("化祿", "貪狼"), ("化權", "太陰"), ("化科", "右弼"), ("化忌", "天機")]


def test_case_a_api_exposes_manual_major_luck_facts() -> None:
    result = post_chart().json()["major_luck"]
    assert (result["year_heavenly_stem"], result["year_yinyang"], result["gender"]) == ("乙", "陰", "female")
    assert (result["direction"], result["bureau_name"], result["bureau_number"]) == ("順行", "土五局", 5)
    assert [
        (row["start_nominal_age"], row["end_nominal_age"], row["earthly_branch"], row["palace_name"], row["palace_ganzhi"]["heavenly_stem"] + row["palace_ganzhi"]["earthly_branch"])
        for row in result["periods"][:5]
    ] == [
        (5, 14, "寅", "命宮", "戊寅"),
        (15, 24, "卯", "父母宮", "己卯"),
        (25, 34, "辰", "福德宮", "庚辰"),
        (35, 44, "巳", "田宅宮", "辛巳"),
        (45, 54, "午", "官祿宮", "壬午"),
    ]


def test_case_a_male_api_changes_only_gender_and_major_luck_direction() -> None:
    female = post_chart().json()
    male = post_chart(gender="male").json()
    assert female["major_luck"]["direction"] == "順行"
    assert male["major_luck"]["direction"] == "逆行"
    female.pop("major_luck")
    male.pop("major_luck")
    female["birth_data"].pop("gender")
    male["birth_data"].pop("gender")
    assert female == male


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


def test_interpret_endpoint_calculates_case_a_and_calls_interpreter_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    class FakeInterpreter:
        async def interpret(self, chart):
            calls.append(chart)
            return InterpretationResult.model_validate(interpretation_payload())

    monkeypatch.setattr(chart_api, "ZiweiInterpreter", FakeInterpreter)
    response = client.post("/api/interpret", json=PRESET_A)
    assert response.status_code == 200
    assert response.json() == interpretation_payload() | {
        "provider": "NVIDIA",
        "model": "z-ai/glm-5.3-flash",
        "model_display_name": "GLM-5.3-Flash",
    }
    assert "NVIDIA_API_KEY" not in response.text
    assert "reasoning_content" not in response.text
    assert len(calls) == 1
    assert calls[0].birth_data.model_dump(mode="json") == PRESET_A
    assert calls[0].life_palace_branch == "寅"
    assert calls[0].body_palace_branch == "寅"
    assert calls[0].five_elements_bureau.bureau_name == "土五局"
    assert len(calls[0].palaces) == 12


def test_invalid_interpret_input_never_calls_interpreter(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    class FakeInterpreter:
        async def interpret(self, chart):
            nonlocal calls
            calls += 1
            return InterpretationResult.model_validate(interpretation_payload())

    monkeypatch.setattr(chart_api, "ZiweiInterpreter", FakeInterpreter)
    response = client.post("/api/interpret", json=PRESET_A | {"birth_hour": 24})
    assert response.status_code == 422
    assert calls == 0


@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    (
        (NvidiaClientError(NvidiaErrorCode.PERMISSION_ERROR, "unsafe detail"), 502, "PERMISSION_ERROR"),
        (NvidiaClientError(NvidiaErrorCode.RATE_LIMIT_ERROR, "unsafe detail"), 429, "RATE_LIMIT_ERROR"),
        (NvidiaClientError(NvidiaErrorCode.TIMEOUT, "unsafe detail"), 504, "TIMEOUT"),
        (InterpretationParseError("unsafe parser detail"), 502, "INVALID_STRUCTURED_RESPONSE"),
    ),
)
def test_interpret_endpoint_returns_safe_errors(
    monkeypatch: pytest.MonkeyPatch, error: Exception, status_code: int, code: str,
) -> None:
    class FailingInterpreter:
        async def interpret(self, chart):
            raise error

    monkeypatch.setattr(chart_api, "ZiweiInterpreter", FailingInterpreter)
    response = client.post("/api/interpret", json=PRESET_A)
    assert response.status_code == status_code
    assert response.json()["detail"]["code"] == code
    assert "unsafe" not in response.text


def test_phase4c_ui_has_explicit_disabled_interpret_control_and_sections() -> None:
    html = client.get("/ziwei").text
    assert 'id="interpret-button" type="button" class="primary" disabled' in html
    for heading in ("總覽", "十二宮解讀", "生年四化解讀", "整體分析"):
        assert heading in html
    assert "只供文化研究與自我反思參考" in html


def test_phase4c_frontend_is_one_click_one_request_and_safe_text_only() -> None:
    javascript = client.get("/static/ziwei.js").text
    assert javascript.count('fetch("/api/interpret"') == 1
    assert 'interpretButton.addEventListener("click"' in javascript
    assert "解盤中，請稍候……" in javascript
    assert "innerHTML" not in javascript
    assert ".textContent" in javascript
    assert 'form.addEventListener("input"' in javascript
    for palace in ("命宮", "兄弟宮", "夫妻宮", "子女宮", "財帛宮", "疾厄宮", "遷移宮", "交友宮", "官祿宮", "田宅宮", "福德宮", "父母宮"):
        assert palace in javascript
    for label in ("性格", "職涯", "財務", "感情", "人際", "家庭", "優勢", "可留意的挑戰"):
        assert label in javascript


def test_openapi_exposes_interpret_endpoint() -> None:
    schema = client.get("/openapi.json").json()
    assert "post" in schema["paths"]["/api/interpret"]
