"""Quan Shu vol.2: 起五行寅例, 六十花甲子納音歌 and five bureau tables.

Source: https://zh.wikisource.org/zh-hant/紫微斗數全書/卷二
The transcription's 甲戊 / 已亥 are resolved to 甲戌 / 己亥 using the
淵海子平 parallel text and canonical Jiazi; see README's source audit.
No dates, palace placement, stars, web calls or LLM calculations live here.
"""

from types import MappingProxyType

from app.models.calendar import (
    EARTHLY_BRANCHES, HEAVENLY_STEMS, CalendarResult, EarthlyBranch,
    Ganzhi, HeavenlyStem,
)
from app.models.ziwei import FiveElement, FiveElementsBureauResult, PalaceLayout


FIVE_TIGER_STARTS = MappingProxyType({
    "甲": "丙", "己": "丙",
    "乙": "戊", "庚": "戊",
    "丙": "庚", "辛": "庚",
    "丁": "壬", "壬": "壬",
    "戊": "甲", "癸": "甲",
})

# Thirty explicit source rows, two valid Jiazi per row. Keep the rows (rather
# than just a dict literal) so duplicate entries cannot be silently overwritten.
# Only the element is part of the public result; names aid human auditing.
NAYIN_ROWS = (
    ("甲子", "乙丑", "金"),  # 海中金
    ("丙寅", "丁卯", "火"),  # 爐中火
    ("戊辰", "己巳", "木"),  # 大林木
    ("庚午", "辛未", "土"),  # 路旁土
    ("壬申", "癸酉", "金"),  # 劍鋒金
    ("甲戌", "乙亥", "火"),  # 山頭火 (not 甲戊)
    ("丙子", "丁丑", "水"),  # 澗下水
    ("戊寅", "己卯", "土"),  # 城頭土
    ("庚辰", "辛巳", "金"),  # 白蠟金
    ("壬午", "癸未", "木"),  # 楊柳木
    ("甲申", "乙酉", "水"),  # 泉中水
    ("丙戌", "丁亥", "土"),  # 屋上土
    ("戊子", "己丑", "火"),  # 霹靂火
    ("庚寅", "辛卯", "木"),  # 松柏木
    ("壬辰", "癸巳", "水"),  # 長流水
    ("甲午", "乙未", "金"),  # 沙中金
    ("丙申", "丁酉", "火"),  # 山下火
    ("戊戌", "己亥", "木"),  # 平地木 (not 已亥)
    ("庚子", "辛丑", "土"),  # 壁上土
    ("壬寅", "癸卯", "金"),  # 金箔金
    ("甲辰", "乙巳", "火"),  # 覆燈火
    ("丙午", "丁未", "水"),  # 天河水
    ("戊申", "己酉", "土"),  # 大驛土
    ("庚戌", "辛亥", "金"),  # 釵釧金
    ("壬子", "癸丑", "木"),  # 桑柘木
    ("甲寅", "乙卯", "水"),  # 大溪水
    ("丙辰", "丁巳", "土"),  # 沙中土
    ("戊午", "己未", "火"),  # 天上火
    ("庚申", "辛酉", "木"),  # 石榴木
    ("壬戌", "癸亥", "水"),  # 大海水
)


def _build_nayin_table() -> dict[str, FiveElement]:
    table = {}
    for first, second, element in NAYIN_ROWS:
        for pair in (first, second):
            if len(pair) != 2 or pair in table:
                raise ValueError(f"invalid or duplicate Na Yin entry: {pair}")
            Ganzhi(heavenly_stem=pair[0], earthly_branch=pair[1])
            table[pair] = FiveElement(element)
    canonical = {
        HEAVENLY_STEMS[i % 10] + EARTHLY_BRANCHES[i % 12] for i in range(60)
    }
    if len(table) != 60 or set(table) != canonical:
        raise ValueError("Na Yin table must contain exactly the 60 valid Jiazi")
    return table


NAYIN_ELEMENTS = MappingProxyType(_build_nayin_table())


def yin_palace_stem(year_heavenly_stem: HeavenlyStem) -> HeavenlyStem:
    """Five-Tiger rule, with explicit validation for direct rule callers."""
    if year_heavenly_stem not in HEAVENLY_STEMS:
        raise ValueError("birth-year stem must be one of the ten heavenly stems")
    return FIVE_TIGER_STARTS[year_heavenly_stem]


def palace_heavenly_stems(
    year_heavenly_stem: HeavenlyStem,
) -> dict[EarthlyBranch, HeavenlyStem]:
    """A fresh branch-keyed map, ordered 寅 through 丑; not palace-name order."""
    start = HEAVENLY_STEMS.index(yin_palace_stem(year_heavenly_stem))
    yin = EARTHLY_BRANCHES.index("寅")
    return {
        EARTHLY_BRANCHES[(yin + offset) % 12]: HEAVENLY_STEMS[(start + offset) % 10]
        for offset in range(12)
    }


def nayin_element(ganzhi: Ganzhi) -> FiveElement:
    """Look up a valid structured Ganzhi, never silently default to an element."""
    # Revalidate even a Ganzhi built with Pydantic's validation-bypass helpers.
    pair = Ganzhi(heavenly_stem=ganzhi.heavenly_stem, earthly_branch=ganzhi.earthly_branch)
    return NAYIN_ELEMENTS[pair.display]


def bureau_from_year_stem_and_life_branch(
    year_heavenly_stem: HeavenlyStem, life_palace_branch: EarthlyBranch,
) -> FiveElementsBureauResult:
    """Low-level rule entry point; does not calculate the Life Palace position."""
    if life_palace_branch not in EARTHLY_BRANCHES:
        raise ValueError("Life Palace must be one of the twelve earthly branches")
    stems = palace_heavenly_stems(year_heavenly_stem)
    life = Ganzhi(heavenly_stem=stems[life_palace_branch], earthly_branch=life_palace_branch)
    return FiveElementsBureauResult(
        year_heavenly_stem=year_heavenly_stem,
        yin_palace_heavenly_stem=stems["寅"],
        life_palace_ganzhi=life,
        nayin_element=nayin_element(life),
    )


def calculate_five_elements_bureau(
    calendar_result: CalendarResult, palace_layout: PalaceLayout,
) -> FiveElementsBureauResult:
    """Consume Phase 1B primary year and Phase 1C Life, from the same birth.

    Caller must pass the layout calculated from this calendar result. The
    primary year already uses Lunar New Year; no second year boundary or
    independent Life Palace placement is introduced here.
    """
    return bureau_from_year_stem_and_life_branch(
        calendar_result.year_ganzhi.heavenly_stem,
        palace_layout.life_palace_branch,
    )
