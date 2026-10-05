"""Phase 1A birth-data and application tests."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.models.birth import BirthData, Gender


def birth_data(**overrides: object) -> BirthData:
    values: dict[str, object] = {
        "name": "Ada",
        "gender": "female",
        "birth_year": 1990,
        "birth_month": 5,
        "birth_day": 20,
        "birth_hour": 14,
        "birth_minute": 30,
        "birthplace": "Taipei",
    }
    values.update(overrides)
    return BirthData.model_validate(values)


def test_valid_birth_data_creation() -> None:
    data = birth_data()

    assert data.birth_year == 1990
    assert data.birth_month == 5
    assert data.birth_day == 20
    assert data.birth_hour == 14
    assert data.birth_minute == 30
    assert data.birthplace == "Taipei"


def test_name_is_optional() -> None:
    assert birth_data(name=None).name is None


def test_male_gender_is_accepted() -> None:
    assert birth_data(gender="male").gender is Gender.MALE


def test_female_gender_is_accepted() -> None:
    assert birth_data(gender="female").gender is Gender.FEMALE


def test_invalid_gender_is_rejected() -> None:
    with pytest.raises(ValidationError):
        birth_data(gender="other")


@pytest.mark.parametrize("month", [0, 13])
def test_invalid_month_is_rejected(month: int) -> None:
    with pytest.raises(ValidationError):
        birth_data(birth_month=month)


def test_impossible_gregorian_date_is_rejected() -> None:
    with pytest.raises(ValidationError):
        birth_data(birth_year=2023, birth_month=2, birth_day=29)


def test_valid_leap_day_is_accepted() -> None:
    data = birth_data(birth_year=2024, birth_month=2, birth_day=29)

    assert (data.birth_year, data.birth_month, data.birth_day) == (2024, 2, 29)


@pytest.mark.parametrize("hour", [-1, 24])
def test_invalid_hour_is_rejected(hour: int) -> None:
    with pytest.raises(ValidationError):
        birth_data(birth_hour=hour)


@pytest.mark.parametrize("minute", [-1, 60])
def test_invalid_minute_is_rejected(minute: int) -> None:
    with pytest.raises(ValidationError):
        birth_data(birth_minute=minute)


@pytest.mark.parametrize("birthplace", ["", "   "])
def test_empty_birthplace_is_rejected(birthplace: str) -> None:
    with pytest.raises(ValidationError):
        birth_data(birthplace=birthplace)


def test_fastapi_application_imports() -> None:
    assert app.title == "Tiger-ZiWei"


def test_health_endpoint() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "project": "Tiger-ZiWei"}
