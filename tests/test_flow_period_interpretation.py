"""Phase 8C Flow-Month/Flow-Day transformations and structured interpretation."""

import asyncio
from copy import deepcopy
from datetime import date, timedelta
import json

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

import app.api.flow_period_interpretation as api_module
import app.llm.flow_period_interpreter as interpreter_module
from app.api.chart import _calculate_input_chart
from app.llm.flow_period_interpreter import (
    FLOW_DAY_SYSTEM_PROMPT,
    FLOW_MONTH_SYSTEM_PROMPT,
    FlowDayInterpreter,
    FlowMonthInterpreter,
    FlowPeriodInterpretationParseError,
    build_flow_day_interpretation_facts,
    build_flow_day_interpretation_messages,
    build_flow_month_interpretation_facts,
    build_flow_month_interpretation_messages,
    parse_flow_day_interpretation_json,
    parse_flow_month_interpretation_json,
    validate_flow_day_fact_lock,
    validate_flow_month_fact_lock,
)
from app.llm.interpreter import INTERPRETATION_MAX_TOKENS, INTERPRETATION_TIMEOUT_SECONDS
from app.llm.nvidia_client import NvidiaClientError, NvidiaErrorCode
from app.main import app
from app.models.birth import BirthInput
from app.models.calendar import HEAVENLY_STEMS
from app.models.flow_date import FlowDayTransformation, FlowMonthTransformation
from app.models.flow_period_interpretation import (
    FlowDayInterpretationResult,
    FlowMonthInterpretationResult,
)
from app.models.flow_query import LunarFlowQueryInput, SolarFlowQueryInput
from app.ziwei.flow_date import _dynamic_transformations
from app.ziwei.flow_query import calculate_flow_query
from app.ziwei.transformations import TRANSFORMATION_TARGETS_BY_STEM


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


def chart(payload=SOLAR_A):
    return _calculate_input_chart(BirthInput.model_validate(payload))


def case_a_flow():
    return calculate_flow_query(chart(), SolarFlowQueryInput(year=2029, month=2, day=13))


def month_payload(month) -> dict:
    return {
        "lunar_year": month.lunar_year,
        "lunar_month": month.lunar_month,
        "is_leap_month": month.is_leap_month,
        "month_ganzhi": month.month_ganzhi.model_dump(mode="json"),
        "flow_month_life_palace_branch": month.flow_month_life_palace_branch,
        "natal_host_palace": month.natal_host_palace_name.value,
        "overview": "此流月可留意節奏與資源配置。",
        "life_palace_analysis": "流月命宮較容易凸顯本命宿宮課題。",
        "major_luck_context": "大限提供十年背景。",
        "flow_year_context": "流年提供年度背景。",
        "transformation_analysis": [
            {
                "transformation_type": item.transformation_type.value,
                "star_name": item.star_name.value,
                "natal_palace_name": item.natal_palace_name.value,
                "analysis": "此流月四化可作為當月觀察重點。",
            }
            for item in month.transformations
        ],
        "career": "職涯可把重點放在可執行事項。",
        "finance": "財務可留意彈性。",
        "relationships": "感情可重視溝通。",
        "family_and_interpersonal": "家庭人際宜釐清界線。",
        "strengths": "優勢在於整合資源。",
        "potential_challenges": "可留意壓力集中。",
        "practical_focus": "適合安排清楚優先順序。",
    }


def day_payload(day) -> dict:
    return {
        "lunar_year": day.target_lunar_year,
        "lunar_month": day.target_lunar_month,
        "lunar_day": day.target_lunar_day,
        "is_leap_month": day.target_is_leap_month,
        "day_ganzhi": day.day_ganzhi.model_dump(mode="json"),
        "flow_day_life_palace_branch": day.flow_day_life_palace_branch,
        "natal_host_palace": day.natal_host_palace_name.value,
        "overview": "此流日可能適合穩健推進。",
        "life_palace_analysis": "流日命宮可留意本命宿宮課題。",
        "major_luck_context": "大限提供十年背景。",
        "flow_year_context": "流年提供年度背景。",
        "flow_month_context": "流月提供當月背景。",
        "transformation_analysis": [
            {
                "transformation_type": item.transformation_type.value,
                "star_name": item.star_name.value,
                "natal_palace_name": item.natal_palace_name.value,
                "analysis": "此流日四化可作為當日觀察重點。",
            }
            for item in day.transformations
        ],
        "work": "工作可先處理明確事項。",
        "finance": "財務可留意小額決策。",
        "relationships": "感情可重視當日溝通。",
        "family_and_interpersonal": "人際宜保持清楚表達。",
        "strengths": "優勢在於聚焦。",
        "potential_challenges": "可留意急躁。",
        "practical_focus": "適合完成當日優先事項。",
    }


class FakeClient:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.calls = []

    async def chat(self, messages, *, max_tokens):
        self.calls.append((messages, max_tokens))
        return self.answer


@pytest.mark.parametrize("stem", HEAVENLY_STEMS)
def test_flow_month_all_ten_stems_reuse_exact_shared_40_assignments(stem) -> None:
    records = _dynamic_transformations(chart(), stem, FlowMonthTransformation)
    assert tuple(item.star_name for item in records) == TRANSFORMATION_TARGETS_BY_STEM[stem]
    assert len(records) == 4


@pytest.mark.parametrize("stem", HEAVENLY_STEMS)
def test_flow_day_all_ten_stems_reuse_exact_shared_40_assignments(stem) -> None:
    records = _dynamic_transformations(chart(), stem, FlowDayTransformation)
    assert tuple(item.star_name for item in records) == TRANSFORMATION_TARGETS_BY_STEM[stem]
    assert len(records) == 4


def test_ren_rule_is_tianfu_for_both_layers_and_preserves_natal_locations() -> None:
    natal = chart()
    month = _dynamic_transformations(natal, "壬", FlowMonthTransformation)
    day = _dynamic_transformations(natal, "壬", FlowDayTransformation)
    for records in (month, day):
        assert tuple(item.star_name.value for item in records) == ("天梁", "紫微", "天府", "武曲")
        for item in records:
            host = next(p for p in natal.palaces if p.earthly_branch == item.natal_branch)
            assert host.palace_name == item.natal_palace_name
            stars = (*host.major_stars, *host.auxiliary_stars)
            assert sum(star.name == item.star_name for star in stars) == 1


def test_case_a_expected_month_and_day_transformations() -> None:
    result = case_a_flow()
    month = result.flow_month
    day = result.flow_day
    assert month is not None and day is not None
    assert (month.month_ganzhi.display, month.flow_month_life_palace_branch) == ("丙寅", "酉")
    assert tuple(item.star_name.value for item in month.transformations) == ("天同", "天機", "文昌", "廉貞")
    assert (day.day_ganzhi.display, day.flow_day_life_palace_branch) == ("甲戌", "酉")
    assert tuple(item.star_name.value for item in day.transformations) == ("廉貞", "破軍", "武曲", "太陽")


def test_fact_models_keep_layers_complete_and_separate() -> None:
    natal = chart()
    result = calculate_flow_query(natal, SolarFlowQueryInput(year=2029, month=2, day=13))
    month_facts = build_flow_month_interpretation_facts(natal, result.flow_year, result.flow_month)
    day_facts = build_flow_day_interpretation_facts(natal, result.flow_year, result.flow_month, result.flow_day)
    assert len(month_facts.flow_year_facts.palaces) == 12
    assert len(month_facts.flow_year_facts.birth_year_transformations) == 4
    assert len(month_facts.flow_month.palaces) == 12
    assert "flow_day" not in month_facts.model_dump(mode="json")
    assert day_facts.flow_month == result.flow_month
    assert day_facts.flow_day == result.flow_day


def test_prompts_require_traditional_chinese_layer_separation_and_scope_limits() -> None:
    natal = chart()
    result = case_a_flow()
    month_facts = build_flow_month_interpretation_facts(natal, result.flow_year, result.flow_month)
    day_facts = build_flow_day_interpretation_facts(natal, result.flow_year, result.flow_month, result.flow_day)
    for required in ("本命", "大限", "流年", "流月", "生年四化", "大限四化", "流年四化", "流月四化", "臺灣常用繁體中文", "流日", "一定", "必然"):
        assert required in FLOW_MONTH_SYSTEM_PROMPT
    for required in ("本命", "大限", "流年", "流月", "流日", "流日四化", "Flow-Hour", "精確時刻", "一定", "必然"):
        assert required in FLOW_DAY_SYSTEM_PROMPT
    month_messages = build_flow_month_interpretation_messages(month_facts)
    day_messages = build_flow_day_interpretation_messages(day_facts)
    assert '"flow_day"' not in month_messages[1]["content"]
    assert '"flow_day"' in day_messages[1]["content"]
    for messages in (month_messages, day_messages):
        assert "DETERMINISTIC FACTS" in messages[1]["content"]
        assert "OUTPUT SCHEMA" in messages[1]["content"]


def test_valid_results_parse_and_pass_fact_lock() -> None:
    natal = chart()
    result = case_a_flow()
    month_facts = build_flow_month_interpretation_facts(natal, result.flow_year, result.flow_month)
    day_facts = build_flow_day_interpretation_facts(natal, result.flow_year, result.flow_month, result.flow_day)
    month = parse_flow_month_interpretation_json(json.dumps(month_payload(result.flow_month), ensure_ascii=False))
    day = parse_flow_day_interpretation_json(json.dumps(day_payload(result.flow_day), ensure_ascii=False))
    validate_flow_month_fact_lock(month_facts, month)
    validate_flow_day_fact_lock(day_facts, day)


@pytest.mark.parametrize(
    "mutator",
    (
        lambda p: p.__setitem__("month_ganzhi", {"heavenly_stem": "丁", "earthly_branch": "卯"}),
        lambda p: p.__setitem__("flow_month_life_palace_branch", "戌"),
        lambda p: p.__setitem__("natal_host_palace", "財帛宮"),
        lambda p: p["transformation_analysis"][0].__setitem__("star_name", "太陽"),
        lambda p: p["transformation_analysis"].pop(),
        lambda p: p["transformation_analysis"][1].__setitem__("transformation_type", "化祿"),
    ),
    ids=("ganzhi", "life", "host", "target", "missing", "duplicate"),
)
def test_flow_month_fact_lock_rejects_changed_missing_or_duplicate_anchors(mutator) -> None:
    natal = chart()
    result = case_a_flow()
    facts = build_flow_month_interpretation_facts(natal, result.flow_year, result.flow_month)
    payload = deepcopy(month_payload(result.flow_month))
    mutator(payload)
    with pytest.raises((FlowPeriodInterpretationParseError, ValidationError)):
        parsed = parse_flow_month_interpretation_json(json.dumps(payload, ensure_ascii=False))
        validate_flow_month_fact_lock(facts, parsed)


@pytest.mark.parametrize(
    "mutator",
    (
        lambda p: p.__setitem__("lunar_day", 2),
        lambda p: p.__setitem__("day_ganzhi", {"heavenly_stem": "乙", "earthly_branch": "亥"}),
        lambda p: p.__setitem__("flow_day_life_palace_branch", "戌"),
        lambda p: p.__setitem__("natal_host_palace", "財帛宮"),
        lambda p: p["transformation_analysis"][2].__setitem__("star_name", "天府"),
        lambda p: p["transformation_analysis"].pop(),
        lambda p: p["transformation_analysis"][1].__setitem__("transformation_type", "化祿"),
    ),
    ids=("date", "ganzhi", "life", "host", "target", "missing", "duplicate"),
)
def test_flow_day_fact_lock_rejects_changed_missing_or_duplicate_anchors(mutator) -> None:
    natal = chart()
    result = case_a_flow()
    facts = build_flow_day_interpretation_facts(natal, result.flow_year, result.flow_month, result.flow_day)
    payload = deepcopy(day_payload(result.flow_day))
    mutator(payload)
    with pytest.raises((FlowPeriodInterpretationParseError, ValidationError)):
        parsed = parse_flow_day_interpretation_json(json.dumps(payload, ensure_ascii=False))
        validate_flow_day_fact_lock(facts, parsed)


@pytest.mark.parametrize("raw", ("not json", "{", "```json\n{}", "prefix {} suffix"))
def test_malformed_or_wrong_schema_is_rejected(raw) -> None:
    with pytest.raises(FlowPeriodInterpretationParseError):
        parse_flow_month_interpretation_json(raw)
    with pytest.raises(FlowPeriodInterpretationParseError):
        parse_flow_day_interpretation_json(raw)


@pytest.mark.parametrize(
    "kind,field,text",
    (
        ("month", "overview", "這個月一定升職。"),
        ("month", "career", "小限顯示工作變化。"),
        ("day", "overview", "下午三點會發生事情。"),
        ("day", "work", "子時必然有結果。"),
        ("day", "practical_focus", "流時可決定精確時刻。"),
    ),
)
def test_results_reject_prophecy_unsupported_astrology_and_exact_hour_claims(kind, field, text) -> None:
    result = case_a_flow()
    payload = month_payload(result.flow_month) if kind == "month" else day_payload(result.flow_day)
    payload[field] = text
    parser = parse_flow_month_interpretation_json if kind == "month" else parse_flow_day_interpretation_json
    with pytest.raises(FlowPeriodInterpretationParseError):
        parser(json.dumps(payload, ensure_ascii=False))


def test_interpreters_make_exactly_one_call_and_reuse_structured_limits() -> None:
    natal = chart()
    result = case_a_flow()
    month_client = FakeClient(json.dumps(month_payload(result.flow_month), ensure_ascii=False))
    day_client = FakeClient(json.dumps(day_payload(result.flow_day), ensure_ascii=False))
    month = asyncio.run(FlowMonthInterpreter(month_client).interpret(natal, result.flow_year, result.flow_month))
    day = asyncio.run(FlowDayInterpreter(day_client).interpret(natal, result.flow_year, result.flow_month, result.flow_day))
    assert isinstance(month, FlowMonthInterpretationResult)
    assert isinstance(day, FlowDayInterpretationResult)
    assert len(month_client.calls) == len(day_client.calls) == 1
    assert month_client.calls[0][1] == day_client.calls[0][1] == INTERPRETATION_MAX_TOKENS


def test_default_interpreters_reuse_existing_timeout(monkeypatch) -> None:
    captured = []

    class CapturingClient:
        def __init__(self, *, timeout):
            captured.append(timeout)

    monkeypatch.setattr(interpreter_module, "NvidiaClient", CapturingClient)
    FlowMonthInterpreter()
    FlowDayInterpreter()
    assert captured == [INTERPRETATION_TIMEOUT_SECONDS, INTERPRETATION_TIMEOUT_SECONDS] == [180.0, 180.0]


def test_endpoints_rebuild_deterministic_layers_and_make_one_mocked_call_each(monkeypatch) -> None:
    result = case_a_flow()
    expected_month = FlowMonthInterpretationResult.model_validate(month_payload(result.flow_month))
    expected_day = FlowDayInterpretationResult.model_validate(day_payload(result.flow_day))
    calls = []

    class FakeMonthInterpreter:
        async def interpret(self, natal, flow_year, flow_month):
            calls.append(("month", flow_year, flow_month))
            return expected_month

    class FakeDayInterpreter:
        async def interpret(self, natal, flow_year, flow_month, flow_day):
            calls.append(("day", flow_year, flow_month, flow_day))
            return expected_day

    monkeypatch.setattr(api_module, "FlowMonthInterpreter", FakeMonthInterpreter)
    monkeypatch.setattr(api_module, "FlowDayInterpreter", FakeDayInterpreter)
    body = {"birth_input": SOLAR_A, "query": {"mode": "solar", "year": 2029, "month": 2, "day": 13}}
    month_response = client.post("/api/flow-month/interpret", json=body)
    day_response = client.post("/api/flow-day/interpret", json=body)
    assert month_response.status_code == day_response.status_code == 200
    assert [call[0] for call in calls] == ["month", "day"]
    assert "NVIDIA_API_KEY" not in month_response.text + day_response.text
    assert "reasoning_content" not in month_response.text + day_response.text


def test_granularity_rejects_unavailable_interpretation_before_provider(monkeypatch) -> None:
    class Forbidden:
        def __init__(self):
            raise AssertionError("provider path must not be constructed")

    monkeypatch.setattr(api_module, "FlowMonthInterpreter", Forbidden)
    monkeypatch.setattr(api_module, "FlowDayInterpreter", Forbidden)
    year_body = {"birth_input": SOLAR_A, "query": {"mode": "lunar", "year": 2029}}
    month_body = {"birth_input": SOLAR_A, "query": {"mode": "lunar", "year": 2029, "month": 1}}
    assert client.post("/api/flow-month/interpret", json=year_body).status_code == 422
    assert client.post("/api/flow-day/interpret", json=year_body).status_code == 422
    assert client.post("/api/flow-day/interpret", json=month_body).status_code == 422


@pytest.mark.parametrize(
    "endpoint,attribute,error,status,code",
    (
        ("/api/flow-month/interpret", "FlowMonthInterpreter", NvidiaClientError(NvidiaErrorCode.TIMEOUT, "unsafe"), 504, "TIMEOUT"),
        ("/api/flow-day/interpret", "FlowDayInterpreter", NvidiaClientError(NvidiaErrorCode.PROVIDER_ERROR, "unsafe"), 502, "PROVIDER_ERROR"),
        ("/api/flow-day/interpret", "FlowDayInterpreter", FlowPeriodInterpretationParseError("unsafe"), 502, "INVALID_STRUCTURED_RESPONSE"),
    ),
)
def test_endpoint_timeout_provider_and_parser_failures_are_sanitized(monkeypatch, endpoint, attribute, error, status, code) -> None:
    class Failing:
        async def interpret(self, *args):
            raise error

    monkeypatch.setattr(api_module, attribute, Failing)
    response = client.post(endpoint, json={
        "birth_input": SOLAR_A,
        "query": {"mode": "solar", "year": 2029, "month": 2, "day": 13},
    })
    assert response.status_code == status
    assert response.json()["detail"]["code"] == code
    assert "unsafe" not in response.text
    assert "NVIDIA_API_KEY" not in response.text


@pytest.mark.parametrize(
    "birth,solar,lunar",
    (
        (SOLAR_A, SolarFlowQueryInput(year=2029, month=2, day=13), LunarFlowQueryInput(year=2029, month=1, day=1)),
        (SOLAR_L, SolarFlowQueryInput(year=2025, month=7, day=25), LunarFlowQueryInput(year=2025, month=6, day=1, is_leap_month=True)),
    ),
)
def test_gregorian_lunar_and_case_l_leap_fact_payloads_are_equivalent(birth, solar, lunar) -> None:
    natal = chart(birth)
    solar_result = calculate_flow_query(natal, solar)
    lunar_result = calculate_flow_query(natal, lunar)
    assert solar_result.flow_month.transformations == lunar_result.flow_month.transformations
    assert solar_result.flow_day.transformations == lunar_result.flow_day.transformations
    assert build_flow_month_interpretation_facts(natal, solar_result.flow_year, solar_result.flow_month) == build_flow_month_interpretation_facts(natal, lunar_result.flow_year, lunar_result.flow_month)
    assert build_flow_day_interpretation_facts(natal, solar_result.flow_year, solar_result.flow_month, solar_result.flow_day) == build_flow_day_interpretation_facts(natal, lunar_result.flow_year, lunar_result.flow_month, lunar_result.flow_day)


def test_openapi_and_ui_buttons_loading_stale_state_safe_rendering_and_word_payload() -> None:
    schema = client.get("/openapi.json").json()
    assert "post" in schema["paths"]["/api/flow-month/interpret"]
    assert "post" in schema["paths"]["/api/flow-day/interpret"]
    html = client.get("/ziwei").text
    javascript = client.get("/static/ziwei.js").text
    for expected in (
        'id="flow-month-interpret-button" type="button" class="primary" disabled>解讀流月',
        'id="flow-day-interpret-button" type="button" class="primary" disabled>解讀流日',
        'id="flow-month-transformation-body"', 'id="flow-day-transformation-body"',
        "流月四化分析", "流日四化分析", "流月背景",
    ):
        assert expected in html
    for expected in (
        'fetchStructuredFlowInterpretation("/api/flow-month/interpret"',
        'fetchStructuredFlowInterpretation("/api/flow-day/interpret"',
        "正在解讀流月……", "正在解讀流日……",
        "invalidateFlowMonthInterpretation();", "invalidateFlowDayInterpretation();",
        "request.flow_month_interpretation = currentFlowMonthInterpretation",
        "request.flow_day_interpretation = currentFlowDayInterpretation",
    ):
        assert expected in javascript
    assert "textContent" in javascript
    assert "innerHTML" not in javascript
    assert javascript.count('fetchStructuredFlowInterpretation("/api/flow-month/interpret"') == 1
    assert javascript.count('fetchStructuredFlowInterpretation("/api/flow-day/interpret"') == 1


def test_nvidia_configuration_remains_shared_across_five_scopes() -> None:
    from app.config import NVIDIA_CLEAR_THINKING, NVIDIA_MODEL, NVIDIA_REASONING_EFFORT

    assert NVIDIA_MODEL == "z-ai/glm-5.3-flash"
    assert NVIDIA_REASONING_EFFORT == "low"
    assert NVIDIA_CLEAR_THINKING is True
