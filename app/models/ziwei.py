"""Minimal, immutable Phase 1C-1E palace, bureau and major-star results."""

from enum import Enum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.models.calendar import EARTHLY_BRANCHES, EarthlyBranch, Ganzhi, HeavenlyStem


class PalaceName(str, Enum):
    """Canonical names in the classical reverse placement order."""

    LIFE = "命宮"
    SIBLINGS = "兄弟宮"
    SPOUSE = "夫妻宮"
    CHILDREN = "子女宮"
    WEALTH = "財帛宮"
    HEALTH = "疾厄宮"
    TRAVEL = "遷移宮"
    FRIENDS = "交友宮"
    CAREER = "官祿宮"
    PROPERTY = "田宅宮"
    FORTUNE = "福德宮"
    PARENTS = "父母宮"


PALACE_ORDER = tuple(PalaceName)
BODY_PALACE_HOSTS = frozenset({
    PalaceName.LIFE, PalaceName.SPOUSE, PalaceName.WEALTH,
    PalaceName.TRAVEL, PalaceName.CAREER, PalaceName.FORTUNE,
})


class PalacePosition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: PalaceName
    earthly_branch: EarthlyBranch
    has_body_palace: bool = Field(strict=True)

    @computed_field
    @property
    def is_life_palace(self) -> bool:
        return self.name is PalaceName.LIFE


class PalaceLayout(BaseModel):
    """Twelve positions with one body marker; no stars or full chart claims.

    Summary fields are derived from the positions so they cannot disagree.
    Use model_dump(round_trip=True) for revalidation without computed fields.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    effective_lunar_month: int = Field(ge=1, le=12, strict=True)
    birth_hour_branch: EarthlyBranch
    palaces: tuple[PalacePosition, ...] = Field(min_length=12, max_length=12)

    @model_validator(mode="after")
    def validate_positions(self) -> Self:
        if tuple(p.name for p in self.palaces) != PALACE_ORDER:
            raise ValueError("palaces must contain the twelve canonical names in order")
        if len({p.earthly_branch for p in self.palaces}) != 12:
            raise ValueError("each earthly branch must contain exactly one palace")
        hosts = [p for p in self.palaces if p.has_body_palace]
        if len(hosts) != 1 or hosts[0].name not in BODY_PALACE_HOSTS:
            raise ValueError("body palace must mark exactly one of the six legal hosts")
        return self

    @computed_field
    @property
    def life_palace_branch(self) -> EarthlyBranch:
        return self.palaces[0].earthly_branch

    @computed_field
    @property
    def body_palace_branch(self) -> EarthlyBranch:
        return next(p.earthly_branch for p in self.palaces if p.has_body_palace)

    @computed_field
    @property
    def body_palace_name(self) -> PalaceName:
        return next(p.name for p in self.palaces if p.has_body_palace)


class FiveElement(str, Enum):
    WATER = "水"
    WOOD = "木"
    METAL = "金"
    EARTH = "土"
    FIRE = "火"

    @property
    def bureau_number(self) -> int:
        # Zi Wei bureau numbers, NOT ordinary elemental numbering.
        return {"水": 2, "木": 3, "金": 4, "土": 5, "火": 6}[self.value]

    @property
    def bureau_name(self) -> str:
        return {"水": "水二局", "木": "木三局", "金": "金四局",
                "土": "土五局", "火": "火六局"}[self.value]


class FiveElementsBureauResult(BaseModel):
    """Deterministic result; redundant display fields are derived, not inputs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    year_heavenly_stem: HeavenlyStem
    yin_palace_heavenly_stem: HeavenlyStem
    life_palace_ganzhi: Ganzhi
    nayin_element: FiveElement

    @computed_field
    @property
    def life_palace_heavenly_stem(self) -> HeavenlyStem:
        return self.life_palace_ganzhi.heavenly_stem

    @computed_field
    @property
    def life_palace_earthly_branch(self) -> EarthlyBranch:
        return self.life_palace_ganzhi.earthly_branch

    @computed_field
    @property
    def bureau_name(self) -> str:
        return self.nayin_element.bureau_name

    @computed_field
    @property
    def bureau_number(self) -> int:
        return self.nayin_element.bureau_number


class MajorStarName(str, Enum):
    ZIWEI = "紫微"
    TIANJI = "天機"
    TAIYANG = "太陽"
    WUQU = "武曲"
    TIANTONG = "天同"
    LIANZHEN = "廉貞"
    TIANFU = "天府"
    TAIYIN = "太陰"
    TANLANG = "貪狼"
    JUMEN = "巨門"
    TIANXIANG = "天相"
    TIANLIANG = "天梁"
    QISHA = "七殺"
    POJUN = "破軍"


class MajorStarPlacement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: MajorStarName
    earthly_branch: EarthlyBranch


class MajorStarChart(BaseModel):
    """Exactly fourteen distinct stars; shared branch locations are normal.

    Summary fields are derived from the validated stars and upstream element.
    No brightness, transformations, luck cycles or interpretation are included.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    lunar_day: int = Field(ge=1, le=30, strict=True)
    bureau_element: FiveElement
    stars: tuple[MajorStarPlacement, ...] = Field(min_length=14, max_length=14)

    @model_validator(mode="after")
    def validate_star_set(self) -> Self:
        if {star.name for star in self.stars} != set(MajorStarName):
            raise ValueError("major-star chart must contain each of the fourteen stars exactly once")
        return self

    @computed_field
    @property
    def bureau_name(self) -> str:
        return self.bureau_element.bureau_name

    @computed_field
    @property
    def bureau_number(self) -> int:
        return self.bureau_element.bureau_number

    @computed_field
    @property
    def ziwei_branch(self) -> EarthlyBranch:
        return next(s.earthly_branch for s in self.stars if s.name is MajorStarName.ZIWEI)

    @computed_field
    @property
    def tianfu_branch(self) -> EarthlyBranch:
        return next(s.earthly_branch for s in self.stars if s.name is MajorStarName.TIANFU)

    @property
    def star_to_branch(self) -> dict[MajorStarName, EarthlyBranch]:
        return {s.name: s.earthly_branch for s in self.stars}

    @property
    def branch_to_stars(self) -> dict[EarthlyBranch, tuple[MajorStarName, ...]]:
        return {b: tuple(s.name for s in self.stars if s.earthly_branch == b)
                for b in EARTHLY_BRANCHES}


class AuxiliaryStarName(str, Enum):
    ZUOFU = "左輔"
    YOUBI = "右弼"
    WENCHANG = "文昌"
    WENQU = "文曲"
    TIANKUI = "天魁"
    TIANYUE = "天鉞"
    LUCUN = "祿存"
    QINGYANG = "擎羊"
    TUOLUO = "陀羅"
    TIANMA = "天馬"
    HUOXING = "火星"
    LINGXING = "鈴星"
    DIKONG = "地空"
    DIJIE = "地劫"


class AuxiliaryStarPlacement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: AuxiliaryStarName
    earthly_branch: EarthlyBranch


class AuxiliaryStarChart(BaseModel):
    """A complete placement result, never a partial or human-acceptance claim."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["PASS"] = "PASS"
    stars: tuple[AuxiliaryStarPlacement, ...] = Field(min_length=14, max_length=14)

    @model_validator(mode="after")
    def validate_star_set(self) -> Self:
        if {s.name for s in self.stars} != set(AuxiliaryStarName):
            raise ValueError("auxiliary chart must contain all fourteen distinct stars")
        return self

    @property
    def star_to_branch(self) -> dict[AuxiliaryStarName, EarthlyBranch]:
        return {s.name: s.earthly_branch for s in self.stars}

    @property
    def branch_to_stars(self) -> dict[EarthlyBranch, tuple[AuxiliaryStarName, ...]]:
        return {b: tuple(s.name for s in self.stars if s.earthly_branch == b)
                for b in EARTHLY_BRANCHES}


class TransformationType(str, Enum):
    HUALU = "化祿"
    HUAQUAN = "化權"
    HUAKE = "化科"
    HUAJI = "化忌"


TRANSFORMATION_ORDER = tuple(TransformationType)


class StarCategory(str, Enum):
    MAJOR = "major"
    AUXILIARY = "auxiliary"


class BirthYearTransformation(BaseModel):
    """One birth-year tag attached to an already-positioned natal star."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    transformation: TransformationType
    star_name: MajorStarName | AuxiliaryStarName
    earthly_branch: EarthlyBranch
    palace_name: PalaceName
    star_category: StarCategory

    @model_validator(mode="after")
    def validate_category(self) -> Self:
        expected = (StarCategory.MAJOR if isinstance(self.star_name, MajorStarName)
                    else StarCategory.AUXILIARY)
        if self.star_category is not expected:
            raise ValueError("star_category must match the target star model")
        return self


class BirthYearTransformations(BaseModel):
    """Exactly one birth-year transformation in canonical 祿權科忌 order."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    year_heavenly_stem: HeavenlyStem
    transformations: tuple[BirthYearTransformation, ...] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def validate_records(self) -> Self:
        if tuple(row.transformation for row in self.transformations) != TRANSFORMATION_ORDER:
            raise ValueError("birth-year transformations must contain 化祿、化權、化科、化忌 in order")
        if len({row.star_name for row in self.transformations}) != 4:
            raise ValueError("birth-year transformation target stars must be unique")
        return self


