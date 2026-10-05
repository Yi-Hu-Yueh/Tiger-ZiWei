"""Offline Phase 1D references, reviewed 2026-10-05.

Primary: https://zh.wikisource.org/zh-hant/紫微斗數全書/卷二
起五行寅例, 六十花甲子納音歌, 安身命例, and five bureau table headings.
Secondary: https://iztro.com/learn/setup (section 12, 定五行局訣).
Transcription audit: https://www.donglishuzhai.net/chapter/5650.html
confirms 甲戌 = 山頭火 and 己亥 = 平地木, not 甲戊 / 已亥.

Literal fixtures are independently transcribed/hand-counted, never generated
by the production implementation. iztro's arithmetic is test-only cross-check
of the entire fixed table; iztro is not installed or called at runtime.
"""

from datetime import date

import pytest
from pydantic import ValidationError

from app.calendar.ganzhi import calculate_calendar
from app.models.birth import BirthData
from app.models.calendar import EARTHLY_BRANCHES, HEAVENLY_STEMS, Ganzhi
from app.models.ziwei import FiveElement, FiveElementsBureauResult
from app.ziwei import calculate_five_elements_bureau, calculate_palaces
from app.ziwei import five_elements as rules


# Independent fixture in canonical cycle order: explicit pair and element.
REFERENCE_NAYIN = (
    ("甲子", "金"), ("乙丑", "金"), ("丙寅", "火"), ("丁卯", "火"),
    ("戊辰", "木"), ("己巳", "木"), ("庚午", "土"), ("辛未", "土"),
    ("壬申", "金"), ("癸酉", "金"), ("甲戌", "火"), ("乙亥", "火"),
    ("丙子", "水"), ("丁丑", "水"), ("戊寅", "土"), ("己卯", "土"),
    ("庚辰", "金"), ("辛巳", "金"), ("壬午", "木"), ("癸未", "木"),
    ("甲申", "水"), ("乙酉", "水"), ("丙戌", "土"), ("丁亥", "土"),
    ("戊子", "火"), ("己丑", "火"), ("庚寅", "木"), ("辛卯", "木"),
    ("壬辰", "水"), ("癸巳", "水"), ("甲午", "金"), ("乙未", "金"),
    ("丙申", "火"), ("丁酉", "火"), ("戊戌", "木"), ("己亥", "木"),
    ("庚子", "土"), ("辛丑", "土"), ("壬寅", "金"), ("癸卯", "金"),
    ("甲辰", "火"), ("乙巳", "火"), ("丙午", "水"), ("丁未", "水"),
    ("戊申", "土"), ("己酉", "土"), ("庚戌", "金"), ("辛亥", "金"),
    ("壬子", "木"), ("癸丑", "木"), ("甲寅", "水"), ("乙卯", "水"),
    ("丙辰", "土"), ("丁巳", "土"), ("戊午", "火"), ("己未", "火"),
    ("庚申", "木"), ("辛酉", "木"), ("壬戌", "水"), ("癸亥", "水"),
)
EXPECTED_BUREAUS = {
    "水": ("水二局", 2), "木": ("木三局", 3), "金": ("金四局", 4),
    "土": ("土五局", 5), "火": ("火六局", 6),
}


def ganzhi(pair: str) -> Ganzhi:
    return Ganzhi(heavenly_stem=pair[0], earthly_branch=pair[1])


@pytest.mark.parametrize("year,start", [
    ("甲", "丙"), ("己", "丙"), ("乙", "戊"), ("庚", "戊"),
    ("丙", "庚"), ("辛", "庚"), ("丁", "壬"), ("壬", "壬"),
    ("戊", "甲"), ("癸", "甲"),
])
def test_all_ten_five_tiger_starts(year: str, start: str) -> None:
    assert rules.yin_palace_stem(year) == start
    assert rules.palace_heavenly_stems(year)["寅"] == start


@pytest.mark.parametrize("years,expected", [
    ("甲己", "丙丁戊己庚辛壬癸甲乙丙丁"),
    ("乙庚", "戊己庚辛壬癸甲乙丙丁戊己"),
    ("丙辛", "庚辛壬癸甲乙丙丁戊己庚辛"),
    ("丁壬", "壬癸甲乙丙丁戊己庚辛壬癸"),
    ("戊癸", "甲乙丙丁戊己庚辛壬癸甲乙"),
])
def test_complete_twelve_position_rotations(years: str, expected: str) -> None:
    for year in years:
        positions = rules.palace_heavenly_stems(year)
        assert "".join(positions) == "寅卯辰巳午未申酉戌亥子丑"
        assert "".join(positions.values()) == expected
        assert len(positions) == 12
        assert set(positions) == set(EARTHLY_BRANCHES)


@pytest.mark.parametrize("branch,pair,element,name,number", [
    ("子", "丙子", "水", "水二局", 2),
    ("寅", "丙寅", "火", "火六局", 6),  # Classical 安身命例 / 爐中火.
    ("辰", "戊辰", "木", "木三局", 3),
    ("午", "庚午", "土", "土五局", 5),
    ("申", "壬申", "金", "金四局", 4),
])
def test_classical_and_all_five_bureau_vectors(
    branch: str, pair: str, element: str, name: str, number: int,
) -> None:
    result = rules.bureau_from_year_stem_and_life_branch("甲", branch)
    assert result.year_heavenly_stem == "甲"
    assert result.yin_palace_heavenly_stem == "丙"
    assert result.life_palace_heavenly_stem == pair[0]
    assert result.life_palace_earthly_branch == branch
    assert result.life_palace_ganzhi.display == pair
    assert result.nayin_element == element
    assert (result.bureau_name, result.bureau_number) == (name, number)


def test_nayin_table_exactly_covers_canonical_sixty_jiazi() -> None:
    raw = [pair for first, second, _ in rules.NAYIN_ROWS for pair in (first, second)]
    canonical = [HEAVENLY_STEMS[i % 10] + EARTHLY_BRANCHES[i % 12] for i in range(60)]
    assert len(raw) == len(set(raw)) == len(rules.NAYIN_ELEMENTS) == 60
    assert raw == canonical
    assert set(rules.NAYIN_ELEMENTS) == set(canonical)
    assert [pair for pair, _ in REFERENCE_NAYIN] == canonical
    for pair, element in rules.NAYIN_ELEMENTS.items():
        assert pair[0] in HEAVENLY_STEMS
        assert pair[1] in EARTHLY_BRANCHES
        assert ganzhi(pair).display == pair
        assert element in {"金", "木", "水", "火", "土"}


@pytest.mark.parametrize("pair,expected", REFERENCE_NAYIN)
def test_all_sixty_elements_against_literal_and_secondary_rule(pair: str, expected: str) -> None:
    assert rules.nayin_element(ganzhi(pair)) == expected
    # iztro section 12's independent arithmetic, used ONLY in tests.
    stem_number = {"甲": 1, "乙": 1, "丙": 2, "丁": 2, "戊": 3,
                   "己": 3, "庚": 4, "辛": 4, "壬": 5, "癸": 5}[pair[0]]
    branch_number = {"子": 1, "丑": 1, "午": 1, "未": 1, "寅": 2, "卯": 2,
                     "申": 2, "酉": 2, "辰": 3, "巳": 3, "戌": 3, "亥": 3}[pair[1]]
    total = stem_number + branch_number
    if total > 5:
        total -= 5
    assert {1: "木", 2: "金", 3: "水", 4: "火", 5: "土"}[total] == expected


def test_five_start_patterns_cover_all_sixty_unique_palace_pairs() -> None:
    results = [
        rules.bureau_from_year_stem_and_life_branch(year, branch)
        for year in "甲乙丙丁戊" for branch in EARTHLY_BRANCHES
    ]
    pairs = [r.life_palace_ganzhi.display for r in results]
    assert len(pairs) == len(set(pairs)) == 60
    assert set(pairs) == {pair for pair, _ in REFERENCE_NAYIN}
    reference = dict(REFERENCE_NAYIN)
    for result in results:
        assert result.nayin_element == reference[result.life_palace_ganzhi.display]
        assert (result.bureau_name, result.bureau_number) == EXPECTED_BUREAUS[result.nayin_element]
    assert {r.bureau_number for r in results} == {2, 3, 4, 5, 6}


@pytest.mark.parametrize("year,branch,pair,element,name,number", [
    ("甲", "子", "丙子", "水", "水二局", 2),
    ("甲", "未", "辛未", "土", "土五局", 5),
    ("戊", "申", "庚申", "木", "木三局", 3),
])
def test_secondary_published_examples(
    year: str, branch: str, pair: str, element: str, name: str, number: int,
) -> None:
    # The three pair/element/bureau vectors are explicitly published by iztro.
    # Year/branch inputs are independently obtained by reversing Five-Tiger.
    result = rules.bureau_from_year_stem_and_life_branch(year, branch)
    assert result.life_palace_ganzhi.display == pair
    assert result.nayin_element == rules.nayin_element(ganzhi(pair)) == element
    assert (result.bureau_name, result.bureau_number) == (name, number)


@pytest.mark.parametrize("pair", ["甲丑", "乙子", "丙卯", "癸戌", "甲戊", "已亥", "A子", "甲A"])
def test_invalid_ganzhi_is_rejected(pair: str) -> None:
    with pytest.raises(ValidationError):
        ganzhi(pair)
    with pytest.raises(ValidationError):
        rules.nayin_element(Ganzhi.model_construct(heavenly_stem=pair[0], earthly_branch=pair[1]))


@pytest.mark.parametrize("year,branch", [("A", "子"), ("甲子", "子"), ("", "子"), ("甲", "甲"), ("甲", "子時")])
def test_invalid_direct_rule_input_is_rejected(year: str, branch: str) -> None:
    with pytest.raises(ValueError):
        rules.bureau_from_year_stem_and_life_branch(year, branch)


@pytest.mark.parametrize("defect", ["duplicate", "missing", "stem", "branch", "parity", "element", "length"])
def test_bad_nayin_data_fails_before_lookup(monkeypatch: pytest.MonkeyPatch, defect: str) -> None:
    rows = list(rules.NAYIN_ROWS)
    if defect == "duplicate":
        rows.append(rows[0])
    elif defect == "missing":
        rows.pop()
    else:
        rows[0] = {
            "stem": ("已子", "乙丑", "金"), "branch": ("甲戊", "乙丑", "金"),
            "parity": ("甲丑", "乙丑", "金"), "element": ("甲子", "乙丑", "風"),
            "length": ("甲子時", "乙丑", "金"),
        }[defect]
    monkeypatch.setattr(rules, "NAYIN_ROWS", tuple(rows))
    with pytest.raises(ValueError):
        rules._build_nayin_table()


# Existing Phase 1C cases: CWA lunar correspondence, hand-counted Life Palace,
# then literal Five-Tiger rotation and classical Na Yin; no code-generated data.
# Includes all eight Phase 1C vectors plus both kinds of year-boundary trap.
FULL_INPUT_VECTORS = [
    ("2025-01-29", 0, 30, (2025, 1, 1, False), "乙", "寅", "戊寅", "土", "土五局", 5),
    ("2025-01-29", 1, 30, (2025, 1, 1, False), "乙", "丑", "己丑", "火", "火六局", 6),
    ("2025-01-29", 3, 30, (2025, 1, 1, False), "乙", "子", "戊子", "火", "火六局", 6),
    ("2024-02-29", 12, 0, (2024, 1, 20, False), "甲", "申", "壬申", "金", "金四局", 4),
    ("2025-07-25", 14, 30, (2025, 6, 1, True), "乙", "丑", "己丑", "火", "火六局", 6),
    ("2025-07-25", 12, 0, (2025, 6, 1, True), "乙", "寅", "戊寅", "土", "土五局", 5),
    ("2025-07-24", 23, 59, (2025, 6, 30, False), "乙", "未", "癸未", "木", "木三局", 3),
    ("2025-07-25", 0, 0, (2025, 6, 1, True), "乙", "申", "甲申", "水", "水二局", 2),
    ("2025-01-28", 0, 30, (2024, 12, 29, False), "甲", "丑", "丁丑", "水", "水二局", 2),
    ("2024-02-09", 0, 30, (2023, 12, 30, False), "癸", "丑", "乙丑", "金", "金四局", 4),
]


def birth(solar: str, hour: int, minute: int) -> BirthData:
    value = date.fromisoformat(solar)
    return BirthData(
        gender="female", birthplace="Taipei", birth_year=value.year,
        birth_month=value.month, birth_day=value.day, birth_hour=hour, birth_minute=minute,
    )


@pytest.mark.parametrize("solar,hour,minute,lunar,year,branch,pair,element,name,number", FULL_INPUT_VECTORS)
def test_full_birth_calendar_palace_bureau_integration(
    solar: str, hour: int, minute: int, lunar: tuple, year: str, branch: str,
    pair: str, element: str, name: str, number: int,
) -> None:
    cal = calculate_calendar(birth(solar, hour, minute))
    layout = calculate_palaces(cal)
    before = (cal.model_dump(), layout.model_dump())
    value = cal.lunar_date
    assert (value.year, value.month, value.day, value.is_leap_month) == lunar
    assert cal.year_ganzhi.heavenly_stem == year
    assert layout.life_palace_branch == branch
    result = calculate_five_elements_bureau(cal, layout)
    assert result.year_heavenly_stem == year
    assert result.life_palace_earthly_branch == branch
    assert result.life_palace_ganzhi.display == pair
    assert result.nayin_element == element
    assert (result.bureau_name, result.bureau_number) == (name, number)
    assert before == (cal.model_dump(), layout.model_dump())


def test_integration_consumes_primary_year_and_existing_layout_only() -> None:
    cal = calculate_calendar(birth("2025-01-29", 0, 30))
    layout = calculate_palaces(cal)
    # Distinct alternative year/day/month values prove the adapter's inputs.
    assert cal.year_ganzhi.heavenly_stem == "乙"
    assert cal.day_ganzhi.heavenly_stem == "戊"
    assert cal.month_ganzhi.heavenly_stem == "丁"
    assert calculate_five_elements_bureau(cal, layout).life_palace_ganzhi.display == "戊寅"
    altered = cal.model_copy(update={"year_ganzhi": ganzhi("甲辰")})
    assert calculate_five_elements_bureau(altered, layout).life_palace_ganzhi.display == "丙寅"
    other_layout = calculate_palaces(calculate_calendar(birth("2025-01-29", 3, 30)))
    # Low-level adapter trusts the supplied layout, not a hidden recalculation.
    assert calculate_five_elements_bureau(cal, other_layout).life_palace_ganzhi.display == "戊子"


def test_serialization_immutability_and_fresh_position_map() -> None:
    result = rules.bureau_from_year_stem_and_life_branch("甲", "寅")
    payload = result.model_dump(mode="json")
    assert payload == {
        "year_heavenly_stem": "甲", "yin_palace_heavenly_stem": "丙",
        "life_palace_ganzhi": {"heavenly_stem": "丙", "earthly_branch": "寅"},
        "life_palace_heavenly_stem": "丙", "life_palace_earthly_branch": "寅",
        "nayin_element": "火", "bureau_name": "火六局", "bureau_number": 6,
    }
    assert FiveElementsBureauResult.model_validate(result.model_dump(round_trip=True)) == result
    with pytest.raises(ValidationError):
        result.nayin_element = FiveElement.WATER
    with pytest.raises(TypeError):
        rules.NAYIN_ELEMENTS["甲子"] = FiveElement.FIRE
    positions = rules.palace_heavenly_stems("甲")
    positions["寅"] = "戊"
    assert rules.palace_heavenly_stems("甲")["寅"] == "丙"


def test_bad_result_element_or_redundant_bureau_override_is_rejected() -> None:
    payload = rules.bureau_from_year_stem_and_life_branch("甲", "寅").model_dump(round_trip=True)
    with pytest.raises(ValidationError):
        FiveElementsBureauResult.model_validate({**payload, "nayin_element": "風"})
    with pytest.raises(ValidationError):
        FiveElementsBureauResult.model_validate({**payload, "bureau_number": 1})
