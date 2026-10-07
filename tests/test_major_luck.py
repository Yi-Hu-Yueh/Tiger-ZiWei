"""Phase 6A deterministic Major-Luck rules and integration tests."""

import json
import os
from pathlib import Path
import shutil
import subprocess

from pydantic import ValidationError
import pytest

from app.birth_input import normalize_birth_input
from app.models.basic_chart import BasicChartResult
from app.models.birth import BirthData, BirthInput
from app.models.calendar import EARTHLY_BRANCHES, HEAVENLY_STEMS
from app.models.major_luck import MajorLuckDirection, MajorLuckPeriod, MajorLuckResult, YearYinYang
from app.ziwei import calculate_basic_chart
from app.ziwei.major_luck import classify_year_stem, determine_major_luck_direction, nominal_age_range
from tests.major_luck_reference import CASE_A_FORWARD, CASE_A_MALE_REVERSE


def case_a(gender: str = "female") -> BirthData:
    return BirthData(
        name="Case A", gender=gender, birth_year=2025, birth_month=1,
        birth_day=29, birth_hour=0, birth_minute=30, birthplace="Taipei",
    )


def normalized_periods(chart: BasicChartResult) -> tuple[tuple[object, ...], ...]:
    return tuple(
        (
            period.index,
            period.start_nominal_age,
            period.end_nominal_age,
            period.earthly_branch,
            period.palace_name.value,
            period.heavenly_stem,
            period.palace_ganzhi.display,
        )
        for period in chart.major_luck.periods
    )


@pytest.mark.parametrize("bureau", (2, 3, 4, 5, 6))
def test_all_five_bureau_start_ages_and_first_three_ranges(bureau: int) -> None:
    assert [nominal_age_range(bureau, index) for index in (1, 2, 3)] == [
        (bureau, bureau + 9), (bureau + 10, bureau + 19), (bureau + 20, bureau + 29),
    ]


@pytest.mark.parametrize("stem", HEAVENLY_STEMS)
def test_all_ten_stems_yinyang_and_gender_direction(stem: str) -> None:
    expected_yinyang = YearYinYang.YANG if stem in "甲丙戊庚壬" else YearYinYang.YIN
    assert classify_year_stem(stem) is expected_yinyang
    assert determine_major_luck_direction(stem, "male") is (
        MajorLuckDirection.FORWARD if expected_yinyang is YearYinYang.YANG else MajorLuckDirection.REVERSE
    )
    assert determine_major_luck_direction(stem, "female") is (
        MajorLuckDirection.REVERSE if expected_yinyang is YearYinYang.YANG else MajorLuckDirection.FORWARD
    )


def test_case_a_complete_forward_fixture() -> None:
    chart = calculate_basic_chart(case_a())
    result = chart.major_luck
    assert (result.year_heavenly_stem, result.year_yinyang, result.gender) == ("乙", YearYinYang.YIN, "female")
    assert (result.direction, result.bureau_name, result.bureau_number) == (MajorLuckDirection.FORWARD, "土五局", 5)
    assert normalized_periods(chart) == CASE_A_FORWARD


def test_case_a_male_complete_reverse_fixture_and_natal_gender_invariance() -> None:
    female = calculate_basic_chart(case_a("female"))
    male = calculate_basic_chart(case_a("male"))
    assert male.major_luck.direction is MajorLuckDirection.REVERSE
    assert normalized_periods(male) == CASE_A_MALE_REVERSE
    assert female.model_dump(exclude={"birth_data", "major_luck"}) == male.model_dump(
        exclude={"birth_data", "major_luck"}
    )
    assert female.major_luck.direction is not male.major_luck.direction


@pytest.mark.parametrize("gender,expected", (("female", CASE_A_FORWARD), ("male", CASE_A_MALE_REVERSE)))
def test_exact_twelve_period_invariants_and_host_palace_reuse(gender: str, expected) -> None:
    chart = calculate_basic_chart(case_a(gender))
    periods = chart.major_luck.periods
    hosts = {palace.earthly_branch: palace for palace in chart.palaces}
    assert normalized_periods(chart) == expected
    assert len(periods) == len({period.earthly_branch for period in periods}) == 12
    assert {period.earthly_branch for period in periods} == set(EARTHLY_BRANCHES)
    for index, period in enumerate(periods):
        assert period.end_nominal_age - period.start_nominal_age + 1 == 10
        assert period.palace_name == hosts[period.earthly_branch].palace_name
        assert period.palace_ganzhi == hosts[period.earthly_branch].palace_ganzhi
        assert period.heavenly_stem == hosts[period.earthly_branch].heavenly_stem
        if index:
            assert periods[index - 1].end_nominal_age + 1 == period.start_nominal_age


def test_forward_and_reverse_branch_sequences_start_at_life_palace() -> None:
    female = calculate_basic_chart(case_a("female"))
    male = calculate_basic_chart(case_a("male"))
    assert tuple(period.earthly_branch for period in female.major_luck.periods) == tuple("寅卯辰巳午未申酉戌亥子丑")
    assert tuple(period.earthly_branch for period in male.major_luck.periods) == tuple("寅丑子亥戌酉申未午巳辰卯")
    assert female.major_luck.periods[0].palace_name.value == "命宮"
    assert male.major_luck.periods[0].palace_name.value == "命宮"


def test_explicit_nominal_age_lookup_has_no_today_dependency() -> None:
    result = calculate_basic_chart(case_a()).major_luck
    assert result.find_by_nominal_age(5) == result.periods[0]
    assert result.find_by_nominal_age(24) == result.periods[1]
    assert result.find_by_nominal_age(4) is None
    assert result.find_by_nominal_age(125) is None
    with pytest.raises(ValueError):
        result.find_by_nominal_age(True)


def test_gregorian_and_lunar_case_a_are_identical() -> None:
    common = dict(name="Case A", gender="female", birth_hour=0, birth_minute=30, birthplace="Taipei")
    solar = BirthInput(**common, calendar_type="solar", birth_year=2025, birth_month=1, birth_day=29)
    lunar = BirthInput(
        **common, calendar_type="lunar", lunar_year=2025, lunar_month=1,
        lunar_day=1, is_leap_month=False,
    )
    assert calculate_basic_chart(normalize_birth_input(solar)).major_luck == calculate_basic_chart(
        normalize_birth_input(lunar)
    ).major_luck


def test_gregorian_and_lunar_leap_month_pair_are_identical() -> None:
    common = dict(name="Case L", gender="female", birth_hour=12, birth_minute=0, birthplace="Taipei")
    solar = BirthInput(**common, calendar_type="solar", birth_year=2025, birth_month=7, birth_day=25)
    lunar = BirthInput(
        **common, calendar_type="lunar", lunar_year=2025, lunar_month=6,
        lunar_day=1, is_leap_month=True,
    )
    assert calculate_basic_chart(normalize_birth_input(solar)).major_luck == calculate_basic_chart(
        normalize_birth_input(lunar)
    ).major_luck


def test_basic_chart_roundtrip_and_major_luck_tamper_rejection() -> None:
    chart = calculate_basic_chart(case_a())
    assert BasicChartResult.model_validate(chart.model_dump(round_trip=True)) == chart
    payload = chart.model_dump(round_trip=True)
    payload["major_luck"]["periods"][1]["earthly_branch"] = "午"
    with pytest.raises(ValidationError):
        BasicChartResult.model_validate(payload)


def test_phase6a_models_have_no_luck_transformations_or_annual_fields() -> None:
    assert set(MajorLuckPeriod.model_fields) == {
        "index", "start_nominal_age", "end_nominal_age", "earthly_branch",
        "palace_name", "heavenly_stem", "palace_ganzhi",
    }
    assert set(MajorLuckResult.model_fields) == {
        "bureau_name", "bureau_number", "year_heavenly_stem", "year_yinyang",
        "gender", "direction", "periods", "period_transformations",
    }


@pytest.fixture(scope="module")
def external_major_luck_report():
    root = Path(__file__).resolve().parents[1]
    node = shutil.which("node")
    receipt = root / "tmp/phase1f-iztro/build-receipt.json"
    if not node or not receipt.exists():
        pytest.skip("pinned iztro development engine/Node absent")
    process = subprocess.run(
        [node, "tests/verify_iztro_major_luck.cjs"], cwd=root, check=False,
        capture_output=True, text=True, encoding="utf-8", env=os.environ,
    )
    assert process.returncode == 0, process.stderr + process.stdout
    return json.loads(process.stdout)


@pytest.mark.parametrize("index", range(3))
def test_pinned_iztro_major_luck_comparison(external_major_luck_report, index: int) -> None:
    row = external_major_luck_report["results"][index]
    chart = calculate_basic_chart(case_a(row["gender"])) if row["case"].startswith("A") else calculate_basic_chart(
        BirthData(
            name="Case C", gender=row["gender"], birth_year=2024, birth_month=2,
            birth_day=29, birth_hour=12, birth_minute=0, birthplace="Taipei",
        )
    )
    tiger = [
        {
            "range": [period.start_nominal_age, period.end_nominal_age],
            "branch": period.earthly_branch,
            "palace": period.palace_name.value,
            "ganzhi": period.palace_ganzhi.display,
        }
        for period in chart.major_luck.periods
    ]
    assert row["direction"] == chart.major_luck.direction.value
    external = [
        {key: period[key] for key in ("range", "branch", "palace", "ganzhi")}
        for period in row["periods"]
    ]
    assert external == tiger
