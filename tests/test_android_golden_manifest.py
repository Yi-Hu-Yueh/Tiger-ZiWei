import hashlib
import json
from pathlib import Path


GOLDEN = Path(__file__).resolve().parents[1] / "android" / "golden"


def test_android_golden_manifest_is_frozen_and_complete() -> None:
    manifest = json.loads((GOLDEN / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_head"] == "36a6254b59df94355a03f0de0e6f05a375f234a0"
    assert manifest["fixture_count"] == 25
    assert len(manifest["files"]) == 25
    for entry in manifest["files"]:
        path = GOLDEN / entry["filename"]
        assert path.stat().st_size == entry["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]


def test_current_python_engine_still_matches_every_frozen_fixture() -> None:
    from pydantic import TypeAdapter
    from scripts.export_android_golden import CASES
    from app.birth_input import normalize_birth_input
    from app.models.birth import BirthInput
    from app.models.flow_query import FlowQueryInput
    from app.ziwei import calculate_basic_chart
    from app.ziwei.flow_year import calculate_flow_year
    from app.ziwei.flow_query import calculate_flow_query
    from app.ziwei.transformations import TRANSFORMATION_TARGETS_BY_STEM
    from app.llm.interpreter import serialize_chart_facts
    from app.llm.major_luck_interpreter import build_major_luck_interpretation_facts
    from app.llm.flow_year_interpreter import build_flow_year_interpretation_facts
    from app.llm.flow_period_interpreter import build_flow_month_interpretation_facts, build_flow_day_interpretation_facts

    def expected(name):
        return json.loads((GOLDEN / name).read_text(encoding="utf-8"))

    charts = {name: calculate_basic_chart(normalize_birth_input(BirthInput.model_validate(payload))) for name, payload in CASES.items()}
    for name, chart in charts.items():
        assert chart.model_dump(mode="json") == expected(f"natal_{name}.json")
    for year in (2026, 2029, 2032, 2039):
        assert calculate_flow_year(charts["A"], year).model_dump(mode="json") == expected(f"flow_year_A_{year}.json")
    assert calculate_flow_year(charts["A_male"], 2039).model_dump(mode="json") == expected("flow_year_A_male_2039.json")
    query_results = {}
    for path in GOLDEN.glob("flow_query_*.json"):
        oracle = expected(path.name)
        query = TypeAdapter(FlowQueryInput).validate_python(oracle["original_query"])
        result = calculate_flow_query(charts["A"], query)
        assert result.model_dump(mode="json") == oracle
        query_results[path.name] = result
    full = query_results["flow_query_A_solar_2029_02_13.json"]
    assert serialize_chart_facts(charts["A"]) == expected("interpretation_facts_natal.json")
    assert build_major_luck_interpretation_facts(charts["A"], 5).model_dump(mode="json") == expected("interpretation_facts_major_luck.json")
    assert build_flow_year_interpretation_facts(charts["A"], full.flow_year).model_dump(mode="json") == expected("interpretation_facts_flow_year.json")
    assert build_flow_month_interpretation_facts(charts["A"], full.flow_year, full.flow_month).model_dump(mode="json") == expected("interpretation_facts_flow_month.json")
    assert build_flow_day_interpretation_facts(charts["A"], full.flow_year, full.flow_month, full.flow_day).model_dump(mode="json") == expected("interpretation_facts_flow_day.json")
    assert {stem: [star.value for star in stars] for stem, stars in TRANSFORMATION_TARGETS_BY_STEM.items()} == expected("transformation_targets.json")
    assert {chart.five_elements_bureau.bureau_name: chart.major_luck.bureau_number for chart in charts.values()}.items() <= expected("bureau_start_ages.json").items()
