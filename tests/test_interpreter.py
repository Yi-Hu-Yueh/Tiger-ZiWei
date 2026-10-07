"""Mocked Phase 4B prompt, parser, schema, and one-call orchestration tests."""

import asyncio
from copy import deepcopy
import json
from typing import Any

import pytest

import app.llm.interpreter as interpreter_module
from app.llm.interpreter import (
    INTERPRETATION_MAX_TOKENS,
    INTERPRETATION_TIMEOUT_SECONDS,
    SYSTEM_PROMPT,
    InterpretationParseError,
    ZiweiInterpreter,
    build_interpretation_messages,
    parse_interpretation_json,
    serialize_chart_facts,
)
from app.models.birth import BirthData
from app.models.ziwei import PalaceName
from app.ziwei import calculate_basic_chart


def case_a_chart():
    return calculate_basic_chart(
        BirthData(
            name="Case A",
            gender="female",
            birth_year=2025,
            birth_month=1,
            birth_day=29,
            birth_hour=0,
            birth_minute=30,
            birthplace="Taipei",
        )
    )


def valid_payload() -> dict[str, Any]:
    return {
        "overview": "從傳統紫微斗數的角度，此命盤可作為自我觀察的參考。",
        "palace_interpretations": [
            {"palace_name": palace.value, "summary": f"{palace.value}配置可用克制方式觀察。"}
            for palace in PalaceName
        ],
        "transformation_analysis": "生年四化依已提供的四個目標解讀，不重新選擇星曜。",
        "overall": {
            "personality": "性格傾向可從既有配置綜合觀察。",
            "career": "職涯方向宜結合現實能力與選擇評估。",
            "finance": "財務傾向只供傳統命理角度參考。",
            "relationships": "感情互動可留意溝通與界線。",
            "interpersonal": "人際模式可能重視互信與分工。",
            "family": "家庭議題宜配合實際生活脈絡理解。",
            "strengths": "優勢在於能整合不同面向。",
            "potential_challenges": "可能的挑戰仍需依個人情境觀察。",
        },
    }


class FakeClient:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.calls: list[tuple[list[dict[str, str]], int]] = []

    async def chat(self, messages, *, max_tokens):
        self.calls.append((messages, max_tokens))
        return self.answer


def test_default_interpreter_uses_dedicated_180_second_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, float] = {}

    class CapturingClient:
        def __init__(self, *, timeout: float) -> None:
            captured["timeout"] = timeout

    monkeypatch.setattr(interpreter_module, "NvidiaClient", CapturingClient)
    interpreter_module.ZiweiInterpreter()
    assert INTERPRETATION_TIMEOUT_SECONDS == 180.0
    assert captured == {"timeout": 180.0}


def test_basic_chart_result_is_serialized_without_recalculation() -> None:
    chart = case_a_chart()
    facts = serialize_chart_facts(chart)
    assert facts["birth"] == {
        "name": "Case A",
        "gender": "female",
        "gregorian_date": "2025-01-29",
        "supplied_civil_time": "00:30",
        "birthplace": "Taipei",
    }
    assert facts["calendar"]["lunar_date"] == {
        "year": 2025,
        "month": 1,
        "day": 1,
        "is_leap_month": False,
    }
    assert facts["calendar"]["effective_natal_month"] == 1


def test_all_twelve_palaces_are_supplied_once() -> None:
    palaces = serialize_chart_facts(case_a_chart())["palaces"]
    assert len(palaces) == 12
    assert {item["palace_name"] for item in palaces} == {palace.value for palace in PalaceName}
    assert sum(item["is_life_palace"] for item in palaces) == 1
    assert sum(item["has_body_palace"] for item in palaces) == 1


def test_all_major_and_auxiliary_stars_are_supplied() -> None:
    palaces = serialize_chart_facts(case_a_chart())["palaces"]
    assert sum(len(item["major_stars"]) for item in palaces) == 14
    assert sum(len(item["auxiliary_stars"]) for item in palaces) == 14


def test_four_transformations_and_exact_targets_are_supplied() -> None:
    facts = serialize_chart_facts(case_a_chart())
    transformations = facts["birth_year_transformations"]
    assert len(transformations) == 4
    assert [(item["transformation"], item["star_name"], item["earthly_branch"], item["palace_name"]) for item in transformations] == [
        ("化祿", "天機", "巳", "田宅宮"),
        ("化權", "天梁", "卯", "父母宮"),
        ("化科", "紫微", "午", "官祿宮"),
        ("化忌", "太陰", "亥", "子女宮"),
    ]
    assert sum(len(item["birth_year_transformations"]) for item in facts["palaces"]) == 4


def test_serialization_contains_only_implemented_fact_sections() -> None:
    facts = serialize_chart_facts(case_a_chart())
    assert set(facts) == {"birth", "calendar", "core", "palaces", "birth_year_transformations"}
    serialized = json.dumps(facts, ensure_ascii=False)
    for forbidden in ("大限", "小限", "流年", "廟旺利陷", "長生十二神", "命主", "身主"):
        assert forbidden not in serialized


def test_prompt_fact_lock_forbids_chart_calculation_and_mutation() -> None:
    messages = build_interpretation_messages(case_a_chart())
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    for required in ("不得計算或重算命盤", "移動／新增／刪除星曜", "改變宮位", "改變生年四化", "嚴禁簡體字", "不得做時間預測"):
        assert required in SYSTEM_PROMPT
    assert "authoritative_chart_facts" in messages[1]["content"]
    assert "不得重新排盤" in messages[1]["content"]


def test_full_valid_plain_json_response_is_parsed() -> None:
    result = parse_interpretation_json(json.dumps(valid_payload(), ensure_ascii=False))
    assert result.overview.startswith("從傳統紫微斗數")
    assert len(result.palace_interpretations) == 12
    assert result.transformation_analysis


def test_one_markdown_json_fence_is_accepted() -> None:
    raw = f"```json\n{json.dumps(valid_payload(), ensure_ascii=False)}\n```"
    assert parse_interpretation_json(raw).overall.career


@pytest.mark.parametrize("raw", ("not json", "{", "```json\n{}", "prefix {} suffix"))
def test_malformed_json_is_rejected(raw: str) -> None:
    with pytest.raises(InterpretationParseError):
        parse_interpretation_json(raw)


def test_missing_palace_is_rejected() -> None:
    payload = valid_payload()
    payload["palace_interpretations"].pop()
    with pytest.raises(InterpretationParseError):
        parse_interpretation_json(json.dumps(payload, ensure_ascii=False))


def test_duplicate_palace_is_rejected() -> None:
    payload = valid_payload()
    payload["palace_interpretations"][-1]["palace_name"] = payload["palace_interpretations"][0]["palace_name"]
    with pytest.raises(InterpretationParseError):
        parse_interpretation_json(json.dumps(payload, ensure_ascii=False))


def test_unknown_palace_is_rejected() -> None:
    payload = valid_payload()
    payload["palace_interpretations"][0]["palace_name"] = "身宮"
    with pytest.raises(InterpretationParseError):
        parse_interpretation_json(json.dumps(payload, ensure_ascii=False))


@pytest.mark.parametrize(
    "mutator",
    (
        lambda payload: payload.__setitem__("overview", " "),
        lambda payload: payload.__setitem__("transformation_analysis", ""),
        lambda payload: payload["palace_interpretations"][0].__setitem__("summary", ""),
        lambda payload: payload["overall"].__setitem__("finance", "  "),
    ),
)
def test_empty_required_text_is_rejected(mutator) -> None:
    payload = valid_payload()
    mutator(payload)
    with pytest.raises(InterpretationParseError):
        parse_interpretation_json(json.dumps(payload, ensure_ascii=False))


def test_all_eight_overall_fields_are_required() -> None:
    expected = {"personality", "career", "finance", "relationships", "interpersonal", "family", "strengths", "potential_challenges"}
    result = parse_interpretation_json(json.dumps(valid_payload(), ensure_ascii=False))
    assert set(result.overall.model_dump()) == expected
    payload = valid_payload()
    payload["overall"].pop("family")
    with pytest.raises(InterpretationParseError):
        parse_interpretation_json(json.dumps(payload, ensure_ascii=False))


def test_unknown_machine_readable_chart_fact_is_rejected() -> None:
    payload = valid_payload()
    payload["palace_interpretations"][0]["earthly_branch"] = "子"
    with pytest.raises(InterpretationParseError):
        parse_interpretation_json(json.dumps(payload, ensure_ascii=False))


def test_interpreter_uses_exactly_one_call_and_preserves_chart() -> None:
    chart = case_a_chart()
    before = deepcopy(chart.model_dump(round_trip=True))
    client = FakeClient(json.dumps(valid_payload(), ensure_ascii=False))
    result = asyncio.run(ZiweiInterpreter(client).interpret(chart))
    assert len(client.calls) == 1
    assert client.calls[0][1] == INTERPRETATION_MAX_TOKENS
    assert len(result.palace_interpretations) == 12
    assert chart.model_dump(round_trip=True) == before
