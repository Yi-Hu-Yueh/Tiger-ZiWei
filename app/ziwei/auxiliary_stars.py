"""Quan Shu vol.2 auxiliary placements; consume Phase 1B, never redo it.

See README Phase 2A-R for the Tiger-ZiWei adopted natal leap-month convention.
Its extension to 左輔/右弼 is an explicit project choice, not a verbatim claim
about the scope of the classical Life/Body paragraph.
"""

from types import MappingProxyType

from app.models.calendar import (
    EARTHLY_BRANCHES, HEAVENLY_STEMS, CalendarResult, EarthlyBranch, Ganzhi,
    HeavenlyStem,
)
from app.models.ziwei import (
    AuxiliaryStarChart, AuxiliaryStarName as Name, AuxiliaryStarPlacement as Placement,
)
from app.ziwei.palace import effective_lunar_month


KUI_YUE = MappingProxyType({
    "甲": ("丑", "未"), "乙": ("子", "申"), "丙": ("亥", "酉"),
    "丁": ("亥", "酉"), "戊": ("丑", "未"), "己": ("子", "申"),
    "庚": ("丑", "未"), "辛": ("午", "寅"), "壬": ("卯", "巳"), "癸": ("卯", "巳"),
})
LU_CUN = MappingProxyType({
    "甲": "寅", "乙": "卯", "丙": "巳", "丁": "午", "戊": "巳",
    "己": "午", "庚": "申", "辛": "酉", "壬": "亥", "癸": "子",
})
# (year branches, horse, fire at 子 hour, bell at 子 hour).
YEAR_GROUPS = (("寅午戌", "申", "丑", "卯"), ("申子辰", "寅", "寅", "戌"),
               ("巳酉丑", "亥", "卯", "戌"), ("亥卯未", "巳", "酉", "戌"))


def _branch_index(branch: EarthlyBranch) -> int:
    if branch not in EARTHLY_BRANCHES:
        raise ValueError("branch must be one of the twelve canonical earthly branches")
    return EARTHLY_BRANCHES.index(branch)


def _move(branch: EarthlyBranch, offset: int) -> EarthlyBranch:
    return EARTHLY_BRANCHES[(_branch_index(branch) + offset) % 12]


def _star(name: Name, branch: EarthlyBranch) -> Placement:
    return Placement(name=name, earthly_branch=branch)


def place_left_right(lunar_month: int) -> tuple[Placement, ...]:
    """Place from an already selected effective natal month (1..12)."""
    if type(lunar_month) is not int or not 1 <= lunar_month <= 12:
        raise ValueError("effective natal month must be an integer from 1 to 12")
    return (_star(Name.ZUOFU, _move("辰", lunar_month - 1)),
            _star(Name.YOUBI, _move("戌", 1 - lunar_month)))


def place_chang_qu(hour: EarthlyBranch) -> tuple[Placement, ...]:
    index = _branch_index(hour)
    return (_star(Name.WENCHANG, _move("戌", -index)),
            _star(Name.WENQU, _move("辰", index)))


def place_kui_yue(stem: HeavenlyStem) -> tuple[Placement, ...]:
    if stem not in HEAVENLY_STEMS:
        raise ValueError("year stem must be a canonical Heavenly Stem")
    kui, yue = KUI_YUE[stem]
    return (_star(Name.TIANKUI, kui), _star(Name.TIANYUE, yue))


def place_lu_yang_tuo(stem: HeavenlyStem) -> tuple[Placement, ...]:
    if stem not in HEAVENLY_STEMS:
        raise ValueError("year stem must be a canonical Heavenly Stem")
    lu = LU_CUN[stem]
    return (_star(Name.LUCUN, lu), _star(Name.QINGYANG, _move(lu, 1)),
            _star(Name.TUOLUO, _move(lu, -1)))


def _year_group(branch: EarthlyBranch) -> tuple[str, str, str, str]:
    _branch_index(branch)
    return next(row for row in YEAR_GROUPS if branch in row[0])


def place_tianma(year_branch: EarthlyBranch) -> tuple[Placement, ...]:
    return (_star(Name.TIANMA, _year_group(year_branch)[1]),)


def place_huo_ling(year_branch: EarthlyBranch, hour: EarthlyBranch) -> tuple[Placement, ...]:
    _, _, fire, bell = _year_group(year_branch)
    index = _branch_index(hour)
    return (_star(Name.HUOXING, _move(fire, index)),
            _star(Name.LINGXING, _move(bell, index)))


def place_kong_jie(hour: EarthlyBranch) -> tuple[Placement, ...]:
    index = _branch_index(hour)
    return (_star(Name.DIKONG, _move("亥", -index)),
            _star(Name.DIJIE, _move("亥", index)))


def calculate_year_hour_stars(year: Ganzhi, hour: EarthlyBranch) -> tuple[Placement, ...]:
    """Twelve placements independent of any lunar-month convention."""
    if not isinstance(year, Ganzhi):
        raise ValueError("year must be a validated Ganzhi object")
    year = Ganzhi.model_validate(year.model_dump(round_trip=True))
    stem, branch = year.heavenly_stem, year.earthly_branch
    return (place_chang_qu(hour) + place_kui_yue(stem) + place_lu_yang_tuo(stem)
            + place_tianma(branch) + place_huo_ling(branch, hour) + place_kong_jie(hour))


def calculate_auxiliary_stars(calendar: CalendarResult) -> AuxiliaryStarChart:
    """Read verified lunar/year/hour data without calculating new upstream data.

    Only 左輔/右弼 use the shared effective natal month. The original lunar
    date and all Ganzhi remain intact; the twelve year/hour stars are unchanged.
    """
    if not isinstance(calendar, CalendarResult):
        raise ValueError("calendar must be a validated CalendarResult object")
    calendar = CalendarResult.model_validate(calendar.model_dump(round_trip=True))
    stars = calculate_year_hour_stars(calendar.year_ganzhi, calendar.hour_ganzhi.earthly_branch)
    month = effective_lunar_month(calendar.lunar_date)
    return AuxiliaryStarChart(stars=place_left_right(month) + stars)
