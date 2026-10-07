"""Compose the verified B-E core. No new astrology formulas or policies."""

from app.calendar.ganzhi import calculate_calendar
from app.models.basic_chart import BasicChartPalace, BasicChartResult, BirthDataSnapshot
from app.models.birth import BirthData
from app.models.calendar import EARTHLY_BRANCHES, Ganzhi
from app.ziwei.five_elements import calculate_five_elements_bureau, palace_heavenly_stems
from app.ziwei.main_stars import calculate_major_stars
from app.ziwei.palace import calculate_palaces
from app.ziwei.auxiliary_stars import calculate_auxiliary_stars
from app.ziwei.transformations import calculate_birth_year_transformations
from app.ziwei.major_luck import calculate_major_luck


def calculate_basic_chart(birth_data: BirthData) -> BasicChartResult:
    """One input, one branch-ordered basic chart; entirely offline/deterministic."""
    if not isinstance(birth_data, BirthData):
        raise ValueError("birth_data must be a validated BirthData object")
    snapshot = BirthDataSnapshot.model_validate(birth_data.model_dump(round_trip=True))
    calendar = calculate_calendar(snapshot)
    layout = calculate_palaces(calendar)
    bureau = calculate_five_elements_bureau(calendar, layout)
    stars = calculate_major_stars(calendar.lunar_date, bureau)
    auxiliary = calculate_auxiliary_stars(calendar)
    transformations = calculate_birth_year_transformations(
        calendar, layout, stars, auxiliary,
    )
    positions = {p.earthly_branch: p for p in layout.palaces}
    stems = palace_heavenly_stems(calendar.year_ganzhi.heavenly_stem)
    palaces = tuple(
        BasicChartPalace(
            palace_name=positions[branch].name,
            palace_ganzhi=Ganzhi(heavenly_stem=stems[branch], earthly_branch=branch),
            has_body_palace=positions[branch].has_body_palace,
            major_stars=tuple(s for s in stars.stars if s.earthly_branch == branch),
            auxiliary_stars=tuple(s for s in auxiliary.stars if s.earthly_branch == branch),
        ) for branch in EARTHLY_BRANCHES
    )
    major_luck = calculate_major_luck(
        year_heavenly_stem=calendar.year_ganzhi.heavenly_stem,
        gender=snapshot.gender,
        bureau=bureau,
        palaces=palaces,
    )
    return BasicChartResult(birth_data=snapshot, calendar=calendar, palace_layout=layout,
                            five_elements_bureau=bureau, major_star_chart=stars,
                            auxiliary_star_chart=auxiliary,
                            birth_year_transformations=transformations, palaces=palaces,
                            major_luck=major_luck)
