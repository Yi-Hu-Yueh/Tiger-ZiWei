"""Phase 6B Major-Luck Four Transformation rules and integration."""

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest
from pydantic import ValidationError

from app.birth_input import normalize_birth_input
from app.llm.nvidia_client import NvidiaClient
from app.models.basic_chart import BasicChartResult
from app.models.birth import BirthData, BirthInput
from app.models.calendar import HEAVENLY_STEMS
from app.models.major_luck import MajorLuckPeriodTransformations, MajorLuckTransformation
from app.models.ziwei import TRANSFORMATION_ORDER
from app.ziwei import calculate_basic_chart
from app.ziwei.major_luck import major_luck_transformation_targets
from app.ziwei.transformations import (
    BIRTH_YEAR_TRANSFORMATION_TARGETS,
    TRANSFORMATION_TARGETS_BY_STEM,
    transformation_targets,
)
from tests.major_luck_reference import (
    CASE_A_FEMALE_TRANSFORMATION_FIXTURE,
    CASE_A_MALE_TRANSFORMATION_TARGETS,
)
from tests.transformation_reference import FORTY_ASSIGNMENTS, TEN_STEM_TABLE, TYPES


def case_a(gender: str = "female") -> BirthData:
    return BirthData(
        name="Case A", gender=gender, birth_year=2025, birth_month=1,
        birth_day=29, birth_hour=0, birth_minute=30, birthplace="Taipei",
    )


def normalized_groups(chart: BasicChartResult):
    periods = {period.index: period for period in chart.major_luck.periods}
    return tuple(
        (
            group.major_luck_index,
            group.start_nominal_age,
            group.end_nominal_age,
            periods[group.major_luck_index].palace_ganzhi.display,
            group.major_luck_palace_name.value,
            tuple(
                (
                    row.transformation_type.value,
                    row.star_name.value,
                    row.star_category.value,
                    row.earthly_branch,
                    row.natal_palace_name.value,
                )
                for row in group.transformations
            ),
        )
        for group in chart.major_luck.period_transformations
    )


def test_all_ten_stems_reuse_phase2b_authoritative_mapping() -> None:
    assert BIRTH_YEAR_TRANSFORMATION_TARGETS is TRANSFORMATION_TARGETS_BY_STEM
    for stem in HEAVENLY_STEMS:
        birth_year = transformation_targets(stem)
        major_luck = major_luck_transformation_targets(stem)
        assert major_luck is birth_year
        assert major_luck is BIRTH_YEAR_TRANSFORMATION_TARGETS[stem]
        assert tuple(star.value for star in major_luck) == TEN_STEM_TABLE[stem]
        assert len(major_luck) == len(set(major_luck)) == 4


def test_exact_same_40_low_level_assignments_as_phase2b_fixture() -> None:
    actual = tuple(
        (stem, transformation, star.value)
        for stem in HEAVENLY_STEMS
        for transformation, star in zip(TYPES, major_luck_transformation_targets(stem), strict=True)
    )
    assert actual == FORTY_ASSIGNMENTS


def test_ren_science_is_tianfu_edition_choice() -> None:
    assert tuple(star.value for star in major_luck_transformation_targets("壬")) == (
        "天梁", "紫微", "天府", "武曲",
    )
    assert major_luck_transformation_targets("壬")[2].value == "天府"


def test_case_a_female_complete_twelve_period_fixture() -> None:
    chart = calculate_basic_chart(case_a("female"))
    assert normalized_groups(chart) == CASE_A_FEMALE_TRANSFORMATION_FIXTURE


def test_case_a_male_complete_reverse_period_fixture() -> None:
    chart = calculate_basic_chart(case_a("male"))
    periods = {period.index: period for period in chart.major_luck.periods}
    actual = tuple(
        (
            group.major_luck_index,
            group.start_nominal_age,
            group.end_nominal_age,
            periods[group.major_luck_index].palace_ganzhi.display,
            group.major_luck_palace_name.value,
            tuple(row.star_name.value for row in group.transformations),
        )
        for group in chart.major_luck.period_transformations
    )
    assert actual == CASE_A_MALE_TRANSFORMATION_TARGETS


def test_female_and_male_first_period_transformations_are_identical() -> None:
    female = calculate_basic_chart(case_a("female")).major_luck
    male = calculate_basic_chart(case_a("male")).major_luck
    assert female.periods[0] == male.periods[0]
    assert female.period_transformations[0] == male.period_transformations[0]
    assert female.periods[1].earthly_branch == "卯"
    assert male.periods[1].earthly_branch == "丑"
    assert female.period_transformations[1].major_luck_heavenly_stem == "己"
    assert male.period_transformations[1].major_luck_heavenly_stem == "己"


@pytest.mark.parametrize("gender", ("female", "male"))
def test_twelve_periods_forty_eight_records_and_natal_location_invariants(gender: str) -> None:
    chart = calculate_basic_chart(case_a(gender))
    groups = chart.major_luck.period_transformations
    natal = {
        star.name: (star.earthly_branch, palace.palace_name, "major")
        for palace in chart.palaces for star in palace.major_stars
    } | {
        star.name: (star.earthly_branch, palace.palace_name, "auxiliary")
        for palace in chart.palaces for star in palace.auxiliary_stars
    }
    assert len(groups) == 12
    assert sum(len(group.transformations) for group in groups) == 48
    for group in groups:
        assert len(group.transformations) == 4
        assert tuple(row.transformation_type for row in group.transformations) == TRANSFORMATION_ORDER
        assert len({row.star_name for row in group.transformations}) == 4
        for row in group.transformations:
            assert row.star_name in natal
            branch, palace_name, category = natal[row.star_name]
            assert (row.earthly_branch, row.natal_palace_name, row.star_category.value) == (
                branch, palace_name, category,
            )


def test_gregorian_lunar_and_leap_month_equivalence_include_transformations() -> None:
    case_a_common = dict(name="Case A", gender="female", birth_hour=0, birth_minute=30, birthplace="Taipei")
    solar_a = BirthInput(**case_a_common, calendar_type="solar", birth_year=2025, birth_month=1, birth_day=29)
    lunar_a = BirthInput(
        **case_a_common, calendar_type="lunar", lunar_year=2025, lunar_month=1,
        lunar_day=1, is_leap_month=False,
    )
    assert calculate_basic_chart(normalize_birth_input(solar_a)).major_luck == calculate_basic_chart(
        normalize_birth_input(lunar_a)
    ).major_luck

    leap_common = dict(name="Case L", gender="female", birth_hour=12, birth_minute=0, birthplace="Taipei")
    solar_l = BirthInput(**leap_common, calendar_type="solar", birth_year=2025, birth_month=7, birth_day=25)
    lunar_l = BirthInput(
        **leap_common, calendar_type="lunar", lunar_year=2025, lunar_month=6,
        lunar_day=1, is_leap_month=True,
    )
    assert calculate_basic_chart(normalize_birth_input(solar_l)).major_luck == calculate_basic_chart(
        normalize_birth_input(lunar_l)
    ).major_luck


@pytest.mark.parametrize("defect", ("target", "branch", "palace", "type", "period_stem"))
def test_basic_chart_rejects_major_luck_transformation_tampering(defect: str) -> None:
    chart = calculate_basic_chart(case_a())
    payload = chart.model_dump(round_trip=True)
    group = payload["major_luck"]["period_transformations"][0]
    row = group["transformations"][0]
    if defect == "target":
        row["star_name"] = "天梁"
    elif defect == "branch":
        row["earthly_branch"] = "寅"
    elif defect == "palace":
        row["natal_palace_name"] = "命宮"
    elif defect == "type":
        row["transformation_type"] = "化權"
    else:
        group["major_luck_heavenly_stem"] = "己"
    with pytest.raises(ValidationError):
        BasicChartResult.model_validate(payload)


def test_models_are_four_transformations_only() -> None:
    assert set(MajorLuckTransformation.model_fields) == {
        "transformation_type", "star_name", "star_category", "earthly_branch", "natal_palace_name",
    }
    assert set(MajorLuckPeriodTransformations.model_fields) == {
        "major_luck_index", "start_nominal_age", "end_nominal_age",
        "major_luck_heavenly_stem", "major_luck_earthly_branch",
        "major_luck_palace_name", "transformations",
    }
    payload = calculate_basic_chart(case_a()).major_luck.model_dump_json()
    assert all(name not in payload for name in ("運昌", "運曲", "運祿", "運羊", "運陀", "運魁", "運鉞", "運馬"))
    assert all(name not in payload for name in ("流年", "yearly", "annual"))


def test_calculation_does_not_call_nvidia(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    async def forbidden_chat(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("NVIDIA must not be called by deterministic Major-Luck calculation")

    monkeypatch.setattr(NvidiaClient, "chat", forbidden_chat)
    chart = calculate_basic_chart(case_a())
    assert len(chart.major_luck.period_transformations) == 12
    assert calls == 0


@pytest.fixture(scope="module")
def external_report():
    root = Path(__file__).resolve().parents[1]
    node = shutil.which("node")
    if not node or not (root / "tmp/phase1f-iztro/build-receipt.json").exists():
        pytest.skip("pinned iztro development engine/Node absent")
    process = subprocess.run(
        [node, "tests/verify_iztro_major_luck.cjs"], cwd=root, check=False,
        capture_output=True, text=True, encoding="utf-8", env=os.environ,
    )
    assert process.returncode == 0, process.stderr + process.stdout
    return json.loads(process.stdout)


@pytest.mark.parametrize("index", (0, 1))
def test_pinned_iztro_period_stems_and_targets_with_ren_variant(external_report, index: int) -> None:
    row = external_report["results"][index]
    chart = calculate_basic_chart(case_a(row["gender"]))
    differences = []
    for external, group in zip(row["periods"], chart.major_luck.period_transformations, strict=True):
        tiger_targets = [item.star_name.value for item in group.transformations]
        assert external["stem"] == group.major_luck_heavenly_stem
        for transformation, tiger, iztro in zip(TYPES, tiger_targets, external["targets"], strict=True):
            if tiger != iztro:
                differences.append({
                    "stem": group.major_luck_heavenly_stem,
                    "transformation": transformation,
                    "tiger": tiger,
                    "external": iztro,
                })
    assert differences == [{
        "stem": "壬", "transformation": "化科", "tiger": "天府", "external": "左輔",
    }]
