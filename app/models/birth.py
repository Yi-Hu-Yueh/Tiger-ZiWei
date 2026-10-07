"""Birth-data domain model."""

from datetime import date
from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Gender(str, Enum):
    """Gender values accepted by the initial birth-data model."""

    MALE = "male"
    FEMALE = "female"


class CalendarType(str, Enum):
    """Calendar used for the user's original date entry."""

    SOLAR = "solar"
    LUNAR = "lunar"


class BirthData(BaseModel):
    """Validated Gregorian birth details.

    ``birth_hour`` and ``birth_minute`` are interpreted exactly as supplied
    civil/standard clock time. True solar time conversion is not implemented.
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    gender: Gender
    birth_year: int
    birth_month: int = Field(ge=1, le=12)
    birth_day: int = Field(ge=1, le=31)
    birth_hour: int = Field(ge=0, le=23)
    birth_minute: int = Field(ge=0, le=59)
    birthplace: str

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        """Trim a supplied name and treat blank input as omitted."""
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("birthplace")
    @classmethod
    def validate_birthplace(cls, value: str) -> str:
        """Require a non-empty birthplace after whitespace is removed."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("birthplace must not be empty")
        return normalized

    @model_validator(mode="after")
    def validate_gregorian_date(self) -> Self:
        """Use the standard library to reject impossible Gregorian dates."""
        try:
            date(self.birth_year, self.birth_month, self.birth_day)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid Gregorian birth date: {exc}") from exc
        return self


class BirthInput(BaseModel):
    """Solar or lunar birth entry that normalizes to the existing BirthData."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    gender: Gender
    calendar_type: CalendarType = CalendarType.SOLAR
    birth_year: int | None = None
    birth_month: int | None = Field(default=None, ge=1, le=12)
    birth_day: int | None = Field(default=None, ge=1, le=31)
    lunar_year: int | None = Field(default=None, ge=1, le=9999)
    lunar_month: int | None = Field(default=None, ge=1, le=12)
    lunar_day: int | None = Field(default=None, ge=1, le=30)
    is_leap_month: bool | None = None
    birth_hour: int = Field(ge=0, le=23)
    birth_minute: int = Field(ge=0, le=59)
    birthplace: str

    @field_validator("name")
    @classmethod
    def normalize_input_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("birthplace")
    @classmethod
    def validate_input_birthplace(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("出生地不可空白")
        return normalized

    @model_validator(mode="after")
    def require_one_date_mode(self) -> Self:
        solar_fields = (self.birth_year, self.birth_month, self.birth_day)
        lunar_fields = (self.lunar_year, self.lunar_month, self.lunar_day)
        if self.calendar_type is CalendarType.SOLAR:
            if any(value is None for value in solar_fields):
                raise ValueError("國曆模式必須提供完整的西元年月日")
            if any(value is not None for value in lunar_fields) or self.is_leap_month is not None:
                raise ValueError("國曆模式不可同時提供農曆日期")
        else:
            if any(value is None for value in lunar_fields) or self.is_leap_month is None:
                raise ValueError("農曆模式必須提供完整年月日與閏月選擇")
            if any(value is not None for value in solar_fields):
                raise ValueError("農曆模式不可同時提供西元日期")
        return self
