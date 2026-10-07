"""Single-call live validation of the Phase 4B Case A interpretation."""

from __future__ import annotations

import asyncio
import os
import re
import sys

from app.config import NVIDIA_MODEL, NVIDIA_REASONING_EFFORT
from app.llm import NvidiaClientError, ZiweiInterpreter
from app.models.birth import BirthData
from app.models.interpretation import InterpretationResult
from app.ziwei import calculate_basic_chart


def _all_text(result: InterpretationResult) -> list[str]:
    return [
        result.overview,
        *(item.summary for item in result.palace_interpretations),
        result.transformation_analysis,
        *result.overall.model_dump().values(),
    ]


def _print_result(result: InterpretationResult) -> None:
    print("\n總覽")
    print(result.overview)
    print("\n十二宮解讀")
    for item in result.palace_interpretations:
        print(f"{item.palace_name.value}：{item.summary}")
    print("\n生年四化")
    print(result.transformation_analysis)
    print("\n整體分析")
    labels = {
        "personality": "性格",
        "career": "職涯",
        "finance": "財務",
        "relationships": "感情",
        "interpersonal": "人際",
        "family": "家庭",
        "strengths": "優勢",
        "potential_challenges": "可留意的挑戰",
    }
    for field, value in result.overall.model_dump().items():
        print(f"{labels[field]}：{value}")


async def _validate() -> int:
    key_source = "PROCESS_ENVIRONMENT" if os.getenv("NVIDIA_API_KEY") else "ABSENT"
    chart = calculate_basic_chart(
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
    print(f"Model: {NVIDIA_MODEL}")
    print(f"Reasoning effort: {NVIDIA_REASONING_EFFORT}")
    print(f"Key source: {key_source}")
    try:
        result = await ZiweiInterpreter().interpret(chart)
    except NvidiaClientError as exc:
        print(f"HTTP/live result: {exc.status_code if exc.status_code is not None else exc.code.value}")
        print(f"Validation result: {exc.code.value}")
        return 1
    except ValueError as exc:
        print("HTTP/live result: RESPONSE_RECEIVED")
        print(f"Validation result: INVALID_STRUCTURED_OUTPUT ({exc})")
        return 1

    texts = _all_text(result)
    has_chinese = all(re.search(r"[\u3400-\u9fff]", text) is not None for text in texts)
    print("HTTP/live result: SUCCESS")
    print(f"Palace analyses: {len(result.palace_interpretations)}")
    print(f"Traditional Chinese text present: {'YES' if has_chinese else 'NO'}")
    print("Validation result: PASS")
    _print_result(result)
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    return asyncio.run(_validate())


if __name__ == "__main__":
    raise SystemExit(main())
