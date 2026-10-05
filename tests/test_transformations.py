"""Phase 2B birth-year Four Transformations and composition invariants."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from pydantic import ValidationError

from app.calendar.ganzhi import calculate_calendar
from app.models.basic_chart import BasicChartResult
from app.models.calendar import CalendarResult, HEAVENLY_STEMS
from app.models.ziwei import (
    AuxiliaryStarName,
    BirthYearTransformation,
    BirthYearTransformations,
    MajorStarName,
    StarCategory,
    TransformationType,
)
from app.ziwei import calculate_basic_chart
from app.ziwei.transformations import (
    BIRTH_YEAR_TRANSFORMATION_TARGETS,
    _locate_target,
    calculate_birth_year_transformations,
    transformation_targets,
)
from scripts.validate_basic_chart import birth
from scripts.validate_transformations import display
from tests.transformation_reference import (
    FORTY_ASSIGNMENTS,
    INTEGRATION_CASES,
    TEN_STEM_TABLE,
    TYPES,
)


ALLOWED_TARGETS = {name.value for name in MajorStarName} | {
    name.value for name in AuxiliaryStarName
}


def normalized_records(chart):
    return tuple(
        (row.transformation.value, row.star_name.value, row.star_category.value,
         row.earthly_branch, row.palace_name.value)
        for row in chart.birth_year_transformations.transformations
    )


def test_independent_static_fixture_has_exactly_40_assignments():
    assert tuple(TEN_STEM_TABLE) == HEAVENLY_STEMS
    assert len(FORTY_ASSIGNMENTS) == len(set(FORTY_ASSIGNMENTS)) == 40
    assert all(transformation in TYPES and star in ALLOWED_TARGETS
               for _, transformation, star in FORTY_ASSIGNMENTS)


@pytest.mark.parametrize("stem", HEAVENLY_STEMS)
def test_complete_ten_stem_table(stem):
    expected = TEN_STEM_TABLE[stem]
    actual = transformation_targets(stem)
    assert tuple(row.value for row in actual) == expected
    assert len(actual) == len(set(actual)) == 4
    assert tuple(row.value for row in BIRTH_YEAR_TRANSFORMATION_TARGETS[stem]) == expected


def test_production_and_static_tables_match_all_40_assignments():
    actual = tuple(
        (stem, transformation, star.value)
        for stem in HEAVENLY_STEMS
        for transformation, star in zip(TYPES, transformation_targets(stem), strict=True)
    )
    assert actual == FORTY_ASSIGNMENTS


@pytest.mark.parametrize("label", tuple(INTEGRATION_CASES))
def test_static_full_integration_cases(label):
    expected = INTEGRATION_CASES[label]
    solar, hour, minute = expected["input"]
    chart = calculate_basic_chart(birth(solar, hour, minute))
    assert chart.year_ganzhi.display == expected["year"]
    assert chart.birth_year_transformations.year_heavenly_stem == expected["year"][0]
    assert normalized_records(chart) == expected["records"]

    existing = {
        row.name.value: row.earthly_branch
        for row in (*chart.major_star_chart.stars, *chart.auxiliary_star_chart.stars)
    }
    assert len(existing) == 28
    assert all(existing[row.star_name.value] == row.earthly_branch
               for row in chart.birth_year_transformations.transformations)
    assert all(next(p.palace_name for p in chart.palaces
                    if p.earthly_branch == row.earthly_branch) is row.palace_name
               for row in chart.birth_year_transformations.transformations)


def test_case_b_allows_two_transformations_in_one_palace():
    chart = calculate_basic_chart(birth("2025-01-29", 1, 30))
    affected = [row for row in chart.birth_year_transformations.transformations
                if row.palace_name.value == "疾厄宮"]
    assert [(row.transformation.value, row.star_name.value) for row in affected] == [
        ("化祿", "天機"), ("化忌", "太陰")]


@pytest.mark.parametrize("stem,auxiliary", [
    ("丙", {"文昌": "化科"}),
    ("戊", {"右弼": "化科"}),
    ("己", {"文曲": "化忌"}),
    ("辛", {"文曲": "化科", "文昌": "化忌"}),
])
def test_auxiliary_targets_preserve_category(stem, auxiliary):
    chart = calculate_basic_chart(birth("2025-01-29", 0, 30))
    data = chart.calendar.model_dump(round_trip=True)
    data["year_ganzhi"]["heavenly_stem"] = stem
    data["year_ganzhi"]["earthly_branch"] = "子" if HEAVENLY_STEMS.index(stem) % 2 == 0 else "丑"
    calendar = CalendarResult.model_validate(data)
    result = calculate_birth_year_transformations(
        calendar, chart.palace_layout, chart.major_star_chart, chart.auxiliary_star_chart,
    )
    selected = {row.star_name.value: row.transformation.value for row in result.transformations
                if row.star_category is StarCategory.AUXILIARY}
    assert selected == auxiliary


def test_resolved_ren_row_targets_existing_tianfu_as_major():
    chart = calculate_basic_chart(birth("2025-01-29", 0, 30))
    data = chart.calendar.model_dump(round_trip=True)
    data["year_ganzhi"]["heavenly_stem"] = "壬"
    data["year_ganzhi"]["earthly_branch"] = "子"
    result = calculate_birth_year_transformations(
        CalendarResult.model_validate(data), chart.palace_layout,
        chart.major_star_chart, chart.auxiliary_star_chart,
    )
    science = result.transformations[2]
    assert (science.transformation.value, science.star_name.value,
            science.star_category.value) == ("化科", "天府", "major")


def test_lunar_new_year_boundary_uses_phase1b_primary_year():
    before = calculate_basic_chart(birth("2025-01-28", 0, 30))
    after = calculate_basic_chart(birth("2025-01-29", 0, 30))
    assert (before.year_ganzhi.display, after.year_ganzhi.display) == ("甲辰", "乙巳")
    assert (before.birth_year_transformations.year_heavenly_stem,
            after.birth_year_transformations.year_heavenly_stem) == ("甲", "乙")
    assert tuple(row.star_name.value for row in before.birth_year_transformations.transformations) == TEN_STEM_TABLE["甲"]
    assert tuple(row.star_name.value for row in after.birth_year_transformations.transformations) == TEN_STEM_TABLE["乙"]


def test_leap_and_late_zi_upstream_values_are_not_mutated():
    for solar, hour, minute in [("2025-07-25", 12, 0), ("2025-07-24", 23, 59)]:
        calendar = calculate_calendar(birth(solar, hour, minute))
        before = calendar.model_dump_json(round_trip=True)
        chart = calculate_basic_chart(birth(solar, hour, minute))
        assert calendar.model_dump_json(round_trip=True) == before
        assert chart.calendar.model_dump_json(round_trip=True) == before
    leap = calculate_basic_chart(birth("2025-07-25", 12, 0))
    late = calculate_basic_chart(birth("2025-07-24", 23, 59))
    assert (leap.lunar_date.month, leap.lunar_date.day, leap.lunar_date.is_leap_month) == (6, 1, True)
    assert (late.solar_date.isoformat(), late.lunar_date.month, late.lunar_date.day,
            late.hour_ganzhi.earthly_branch) == ("2025-07-24", 6, 30, "子")


def test_target_existence_helper_rejects_missing_and_duplicate():
    target = MajorStarName.TIANJI
    with pytest.raises(ValueError, match="天機 must exist exactly once"):
        _locate_target(target, [])
    row = (target, "巳", StarCategory.MAJOR)
    with pytest.raises(ValueError, match="天機 must exist exactly once"):
        _locate_target(target, [row, row])


def test_models_reject_invalid_order_duplicate_category_and_count():
    chart = calculate_basic_chart(birth("2025-01-29", 0, 30))
    data = chart.birth_year_transformations.model_dump(round_trip=True)
    first = dict(data["transformations"][0])
    with pytest.raises(ValidationError):
        BirthYearTransformations.model_validate({**data, "transformations": data["transformations"][:3]})
    duplicate = [dict(row) for row in data["transformations"]]
    duplicate[1]["star_name"] = duplicate[0]["star_name"]
    with pytest.raises(ValidationError, match="target stars must be unique"):
        BirthYearTransformations.model_validate({**data, "transformations": duplicate})
    reordered = list(data["transformations"])
    reordered[0], reordered[1] = reordered[1], reordered[0]
    with pytest.raises(ValidationError, match="in order"):
        BirthYearTransformations.model_validate({**data, "transformations": reordered})
    first["star_category"] = "auxiliary"
    with pytest.raises(ValidationError, match="star_category"):
        BirthYearTransformation.model_validate(first)


@pytest.mark.parametrize("field", ["transformation", "star_name", "earthly_branch", "palace_name", "star_category", "year_heavenly_stem"])
def test_basic_chart_rejects_transformation_tampering(field):
    chart = calculate_basic_chart(birth("2025-01-29", 0, 30))
    data = chart.model_dump(round_trip=True)
    if field == "year_heavenly_stem":
        data["birth_year_transformations"][field] = "甲"
    else:
        row = data["birth_year_transformations"]["transformations"][0]
        replacements = {"transformation": "化權", "star_name": "天梁", "earthly_branch": "子",
                        "palace_name": "命宮", "star_category": "auxiliary"}
        row[field] = replacements[field]
    with pytest.raises(ValidationError):
        BasicChartResult.model_validate(data)


def test_deterministic_and_json_roundtrip():
    value = birth("2025-01-29", 0, 30)
    first, second = calculate_basic_chart(value), calculate_basic_chart(value)
    assert first.birth_year_transformations == second.birth_year_transformations
    payload = first.model_dump_json(round_trip=True)
    assert BasicChartResult.model_validate_json(payload) == first
    assert payload == second.model_dump_json(round_trip=True)


def test_manual_tool_contains_table_and_all_cases():
    process = subprocess.run(
        [sys.executable, "-m", "scripts.validate_transformations"],
        cwd=Path(__file__).resolve().parents[1], capture_output=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert process.returncode == 0, process.stderr
    text = process.stdout.decode("utf-8")
    assert all(f"CASE {label}" in text for label in "ABCLZ")
    assert "FINAL VERIFIED TEN-STEM TABLE" in text
    assert "壬: 化祿=天梁 / 化權=紫微 / 化科=天府 / 化忌=武曲" in text
    assert "palace-stem" not in text.lower()
    chart = calculate_basic_chart(birth("2025-01-29", 0, 30))
    assert "化祿 | 天機 | major | 巳 | 田宅宮" in display(chart)


@pytest.fixture(scope="module")
def external_report():
    root = Path(__file__).resolve().parents[1]
    node = shutil.which("node")
    if not node or not (root / "tmp/phase1f-iztro/build-receipt.json").exists():
        pytest.skip("optional pinned iztro/Node dev engine absent; Python Phase 2B needs neither")
    process = subprocess.run(
        [node, "tests/verify_iztro_transformations.cjs"], cwd=root,
        capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "TIGER_PYTHON": sys.executable},
    )
    assert process.returncode == 0, process.stderr + process.stdout
    return json.loads(process.stdout)


def test_optional_iztro_full_table(external_report):
    assert external_report["compared_assignments"] == 40
    assert external_report["classification"] == "EDITION_VARIANT"
    assert external_report["differences"] == [
        {"stem": "壬", "transformation": "化科", "tiger": "天府", "external": "左輔"}
    ]


@pytest.mark.parametrize("label", tuple(INTEGRATION_CASES))
def test_optional_iztro_chart_locations(external_report, label):
    row = next(item for item in external_report["cases"] if item["case"] == label)
    if label == "L":
        assert row["classification"] == "DIFFERENT_CONVENTION"
        assert row["target_names_match"] is True
    else:
        assert row["classification"] == "MATCH"
        assert row["differences"] == []
