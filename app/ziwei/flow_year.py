"""Deterministic annual palace rotation for one explicit Chinese lunar year."""

from app.calendar.ganzhi import calculate_lunar_year_ganzhi
from app.models.basic_chart import BasicChartResult
from app.models.calendar import EARTHLY_BRANCHES, EarthlyBranch, HeavenlyStem
from app.models.flow_year import FlowYearPalace, FlowYearResult, FlowYearTransformation
from app.models.ziwei import PalaceName, StarCategory, TRANSFORMATION_ORDER
from app.ziwei.transformations import (
    TransformationStarName,
    _locate_target,
    transformation_targets,
)


FLOW_YEAR_PALACE_ORDER: tuple[PalaceName, ...] = (
    PalaceName.LIFE,
    PalaceName.PARENTS,
    PalaceName.FORTUNE,
    PalaceName.PROPERTY,
    PalaceName.CAREER,
    PalaceName.FRIENDS,
    PalaceName.TRAVEL,
    PalaceName.HEALTH,
    PalaceName.WEALTH,
    PalaceName.CHILDREN,
    PalaceName.SPOUSE,
    PalaceName.SIBLINGS,
)


def flow_year_palace_branches(life_branch: EarthlyBranch) -> tuple[EarthlyBranch, ...]:
    """Rotate forward over 子丑…亥 from the explicit annual Life branch."""

    if life_branch not in EARTHLY_BRANCHES:
        raise ValueError("unsupported Flow-Year Life Palace branch")
    start = EARTHLY_BRANCHES.index(life_branch)
    return tuple(EARTHLY_BRANCHES[(start + offset) % 12] for offset in range(12))


def flow_year_transformation_targets(
    stem: HeavenlyStem,
) -> tuple[TransformationStarName, ...]:
    """Select the shared Phase 2B row using only the Flow-Year stem."""

    return transformation_targets(stem)


def calculate_flow_year(chart: BasicChartResult, target_year: int) -> FlowYearResult:
    """Calculate the Phase 6C core and Phase 6D annual transformations."""

    if not isinstance(chart, BasicChartResult):
        raise ValueError("chart must be a validated BasicChartResult")
    year_ganzhi = calculate_lunar_year_ganzhi(target_year)
    birth_lunar_year = chart.calendar.lunar_date.year
    if target_year < birth_lunar_year:
        raise ValueError("target lunar year cannot be earlier than the birth lunar year")

    nominal_age = target_year - birth_lunar_year + 1
    active_major_luck = chart.major_luck.find_by_nominal_age(nominal_age)
    first_period = chart.major_luck.periods[0]
    last_period = chart.major_luck.periods[-1]
    host_by_branch = {palace.earthly_branch: palace for palace in chart.palaces}
    if set(host_by_branch) != set(EARTHLY_BRANCHES):
        raise ValueError("Flow-Year calculation requires all twelve natal palace branches")

    branches = flow_year_palace_branches(year_ganzhi.earthly_branch)
    palaces = tuple(
        FlowYearPalace(
            flow_palace_name=flow_name,
            earthly_branch=branch,
            natal_palace_name=host_by_branch[branch].palace_name,
            natal_palace_heavenly_stem=host_by_branch[branch].heavenly_stem,
            natal_palace_ganzhi=host_by_branch[branch].palace_ganzhi,
        )
        for flow_name, branch in zip(FLOW_YEAR_PALACE_ORDER, branches, strict=True)
    )
    existing_stars = [
        (star.name, star.earthly_branch, StarCategory.MAJOR)
        for palace in chart.palaces for star in palace.major_stars
    ] + [
        (star.name, star.earthly_branch, StarCategory.AUXILIARY)
        for palace in chart.palaces for star in palace.auxiliary_stars
    ]
    transformations = []
    for transformation_type, target in zip(
        TRANSFORMATION_ORDER,
        flow_year_transformation_targets(year_ganzhi.heavenly_stem),
        strict=True,
    ):
        _, branch, category = _locate_target(target, existing_stars)
        host = host_by_branch[branch]
        transformations.append(
            FlowYearTransformation(
                transformation_type=transformation_type,
                star_name=target,
                star_category=category,
                earthly_branch=branch,
                natal_palace_name=host.palace_name,
            )
        )
    return FlowYearResult(
        target_lunar_year=target_year,
        heavenly_stem=year_ganzhi.heavenly_stem,
        earthly_branch=year_ganzhi.earthly_branch,
        ganzhi=year_ganzhi,
        nominal_age=nominal_age,
        flow_life_palace_branch=year_ganzhi.earthly_branch,
        palaces=palaces,
        transformations=tuple(transformations),
        active_major_luck=active_major_luck,
        before_first_major_luck=nominal_age < first_period.start_nominal_age,
        after_supported_major_luck=nominal_age > last_period.end_nominal_age,
    )
