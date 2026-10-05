"""Birth-data domain model."""

from datetime import date
from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Gender(str, Enum):
    """Gender values accepted by the initial birth-data model."""

    MALE = "male"
    FEMALE = "female"


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
