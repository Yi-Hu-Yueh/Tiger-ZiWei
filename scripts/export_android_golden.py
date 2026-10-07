"""Freeze accepted Python outputs as the standalone Android migration oracle.

This script is intentionally manual. Android builds and tests never invoke it.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pydantic import TypeAdapter

from app.birth_input import normalize_birth_input
from app.llm.flow_period_interpreter import (
    build_flow_day_interpretation_facts,
    build_flow_month_interpretation_facts,
)
from app.llm.flow_year_interpreter import build_flow_year_interpretation_facts
from app.llm.interpreter import serialize_chart_facts
from app.llm.major_luck_interpreter import build_major_luck_interpretation_facts
from app.models.birth import BirthInput
from app.models.flow_query import FlowQueryInput
from app.ziwei import calculate_basic_chart
from app.ziwei.flow_query import calculate_flow_query
from app.ziwei.flow_year import calculate_flow_year
from app.ziwei.transformations import TRANSFORMATION_TARGETS_BY_STEM


OUTPUT = ROOT / "android" / "golden"

CASES = {
    "A": dict(name="Case A", gender="female", calendar_type="solar", birth_year=2025,
              birth_month=1, birth_day=29, birth_hour=0, birth_minute=30, birthplace="Taipei"),
    "B": dict(name="Case B", gender="female", calendar_type="solar", birth_year=2025,
              birth_month=1, birth_day=29, birth_hour=1, birth_minute=30, birthplace="Taipei"),
    "C": dict(name="Case C", gender="female", calendar_type="solar", birth_year=2024,
              birth_month=2, birth_day=29, birth_hour=12, birth_minute=0, birthplace="Taipei"),
    "L": dict(name="Case L", gender="female", calendar_type="solar", birth_year=2025,
              birth_month=7, birth_day=25, birth_hour=12, birth_minute=0, birthplace="Taipei"),
    "Z": dict(name="Case Z", gender="female", calendar_type="solar", birth_year=2025,
              birth_month=7, birth_day=24, birth_hour=23, birth_minute=59, birthplace="Taipei"),
    "A_male": dict(name="Case A Male", gender="male", calendar_type="solar", birth_year=2025,
                   birth_month=1, birth_day=29, birth_hour=0, birth_minute=30, birthplace="Taipei"),
}


def dump(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def model_json(model):
    return model.model_dump(mode="json")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    charts = {}
    for name, payload in CASES.items():
        birth_input = BirthInput.model_validate(payload)
        chart = calculate_basic_chart(normalize_birth_input(birth_input))
        charts[name] = chart
        dump(OUTPUT / f"natal_{name}.json", model_json(chart))

    for year in (2026, 2029, 2032, 2039):
        dump(OUTPUT / f"flow_year_A_{year}.json", model_json(calculate_flow_year(charts["A"], year)))
    dump(OUTPUT / "flow_year_A_male_2039.json", model_json(calculate_flow_year(charts["A_male"], 2039)))

    queries = {
        "solar_2029_02_12": {"mode": "solar", "year": 2029, "month": 2, "day": 12},
        "solar_2029_02_13": {"mode": "solar", "year": 2029, "month": 2, "day": 13},
        "lunar_2026_year": {"mode": "lunar", "year": 2026},
        "lunar_2026_month10": {"mode": "lunar", "year": 2026, "month": 10, "is_leap_month": False},
        "lunar_2026_month10_day7": {
            "mode": "lunar", "year": 2026, "month": 10, "day": 7, "is_leap_month": False,
        },
        "solar_2025_07_25": {"mode": "solar", "year": 2025, "month": 7, "day": 25},
        "lunar_2025_leap6_day1": {
            "mode": "lunar", "year": 2025, "month": 6, "day": 1, "is_leap_month": True,
        },
    }
    query_results = {}
    for name, payload in queries.items():
        result = calculate_flow_query(charts["A"], TypeAdapter(FlowQueryInput).validate_python(payload))
        query_results[name] = result
        dump(OUTPUT / f"flow_query_A_{name}.json", model_json(result))

    dump(
        OUTPUT / "transformation_targets.json",
        {stem: [star.value for star in stars] for stem, stars in TRANSFORMATION_TARGETS_BY_STEM.items()},
    )
    dump(
        OUTPUT / "bureau_start_ages.json",
        {"水二局": 2, "木三局": 3, "金四局": 4, "土五局": 5, "火六局": 6},
    )

    full = query_results["solar_2029_02_13"]
    assert full.flow_month is not None and full.flow_day is not None
    facts = {
        "natal": serialize_chart_facts(charts["A"]),
        "major_luck": model_json(build_major_luck_interpretation_facts(charts["A"], 5)),
        "flow_year": model_json(build_flow_year_interpretation_facts(charts["A"], full.flow_year)),
        "flow_month": model_json(build_flow_month_interpretation_facts(
            charts["A"], full.flow_year, full.flow_month,
        )),
        "flow_day": model_json(build_flow_day_interpretation_facts(
            charts["A"], full.flow_year, full.flow_month, full.flow_day,
        )),
    }
    for name, payload in facts.items():
        dump(OUTPUT / f"interpretation_facts_{name}.json", payload)

    files = sorted(path for path in OUTPUT.glob("*.json") if path.name != "manifest.json")
    manifest = {
        "format": 1,
        "source": "accepted Tiger-ZiWei Python engine",
        "source_head": subprocess.check_output(
            ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
        ).strip(),
        "fixture_count": len(files),
        "files": [
            {
                "filename": path.name,
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in files
        ],
    }
    dump(OUTPUT / "manifest.json", manifest)


if __name__ == "__main__":
    main()
