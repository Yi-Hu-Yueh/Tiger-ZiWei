"""Explicit calendar results; lunar months are not Ganzhi months."""

from datetime import date, time
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

HeavenlyStem = Literal["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
EarthlyBranch = Literal["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
HEAVENLY_STEMS: tuple[HeavenlyStem, ...] = (
    "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸",
)
EARTHLY_BRANCHES: tuple[EarthlyBranch, ...] = (
    "子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥",
)
SUPPORTED_GREGORIAN_START = date(1582, 10, 15)


class LunarDate(BaseModel):
    """Lunar year/month/day; actual month existence is checked on conversion."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    year: int = Field(ge=1, le=9999, strict=True)
    month: int = Field(ge=1, le=12, strict=True)
    day: int = Field(ge=1, le=30, strict=True)
    is_leap_month: bool = Field(strict=True)


class Ganzhi(BaseModel):
    """A valid pair from the sexagenary cycle, stored as Chinese characters."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    heavenly_stem: HeavenlyStem
    earthly_branch: EarthlyBranch

    @model_validator(mode="after")
    def validate_pair(self) -> Self:
        if HEAVENLY_STEMS.index(self.heavenly_stem) % 2 != (
            EARTHLY_BRANCHES.index(self.earthly_branch) % 2
        ):
            raise ValueError("stem and branch must form a valid sexagenary pair")
        return self

    @property
    def display(self) -> str:
        return self.heavenly_stem + self.earthly_branch


class CalendarResult(BaseModel):
    """Calendar infrastructure output, not a Zi Wei chart or a Bazi chart."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    solar_date: date
    solar_time: time
    lunar_date: LunarDate
    year_ganzhi: Ganzhi
    month_ganzhi: Ganzhi
    day_ganzhi: Ganzhi
    hour_ganzhi: Ganzhi
    time_basis: Literal["supplied_civil_standard_time"] = "supplied_civil_standard_time"
    year_boundary: Literal["lunar_new_year"] = "lunar_new_year"
    month_boundary: Literal["solar_term_civil_date"] = "solar_term_civil_date"
    day_boundary: Literal["civil_midnight"] = "civil_midnight"
    hour_policy: Literal["civil_day_stem_no_23h_rollover"] = "civil_day_stem_no_23h_rollover"
