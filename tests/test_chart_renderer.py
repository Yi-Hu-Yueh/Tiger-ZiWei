"""Phase 3A formal PNG renderer and HTTP integration tests."""

from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image
import pytest

import app.api.chart as chart_api
from app.chart.renderer import (
    BRANCH_GRID_POSITIONS,
    CANVAS_SIZE,
    CENTER_SECTION_TITLES,
    _center_details,
    _star_display_items,
    find_chinese_font,
    render_chart_png,
)
from app.main import app
from app.models.birth import BirthData
from app.ziwei import calculate_basic_chart


client = TestClient(app)

PRESETS = {
    "A": (2025, 1, 29, 0, 30),
    "B": (2025, 1, 29, 1, 30),
    "C": (2024, 2, 29, 12, 0),
    "L": (2025, 7, 25, 12, 0),
    "Z": (2025, 7, 24, 23, 59),
}


def birth_data(case: str, *, name: str | None = None) -> BirthData:
    year, month, day, hour, minute = PRESETS[case]
    return BirthData(
        name=name if name is not None else f"預設 {case}",
        gender="female",
        birth_year=year,
        birth_month=month,
        birth_day=day,
        birth_hour=hour,
        birth_minute=minute,
        birthplace="Taipei",
    )


def assert_png(path: Path) -> None:
    assert path.is_file()
    assert path.stat().st_size > 10_000
    with Image.open(path) as image:
        assert image.format == "PNG"
        assert image.size == (CANVAS_SIZE, CANVAS_SIZE)
        image.verify()


def test_renderer_produces_nonempty_png(tmp_path: Path) -> None:
    artifact = render_chart_png(calculate_basic_chart(birth_data("A")), tmp_path)
    assert_png(artifact.path)


@pytest.mark.parametrize("case", tuple(PRESETS))
def test_renderer_works_for_manual_presets(case: str, tmp_path: Path) -> None:
    artifact = render_chart_png(calculate_basic_chart(birth_data(case)), tmp_path)
    assert_png(artifact.path)
    assert artifact.filename == f"預設_{case}_紫微命盤.png"


def test_renderer_does_not_mutate_structured_chart(tmp_path: Path) -> None:
    chart = calculate_basic_chart(birth_data("A"))
    before = chart.model_dump(round_trip=True)
    render_chart_png(chart, tmp_path)
    assert chart.model_dump(round_trip=True) == before


def test_renderer_is_deterministic_for_same_input(tmp_path: Path) -> None:
    chart = calculate_basic_chart(birth_data("B"))
    first = render_chart_png(chart, tmp_path)
    first_bytes = first.path.read_bytes()
    second = render_chart_png(chart, tmp_path)
    assert second.path == first.path
    assert second.path.read_bytes() == first_bytes


def test_no_name_filename_uses_birth_datetime(tmp_path: Path) -> None:
    unnamed = birth_data("A").model_copy(update={"name": None})
    artifact = render_chart_png(calculate_basic_chart(unnamed), tmp_path)
    assert artifact.filename == "2025-01-29_0030_紫微命盤.png"


def test_traditional_branch_grid_is_complete_and_stable() -> None:
    assert BRANCH_GRID_POSITIONS == {
        "巳": (0, 0), "午": (1, 0), "未": (2, 0), "申": (3, 0),
        "辰": (0, 1), "酉": (3, 1), "卯": (0, 2), "戌": (3, 2),
        "寅": (0, 3), "丑": (1, 3), "子": (2, 3), "亥": (3, 3),
    }
    assert len(set(BRANCH_GRID_POSITIONS.values())) == 12


def test_center_panel_has_all_refined_groups() -> None:
    assert CENTER_SECTION_TITLES == ("基本資料", "曆法", "命盤", "月規則", "生年四化")


def test_render_data_contains_all_palaces_and_stars() -> None:
    chart = calculate_basic_chart(birth_data("A"))
    assert len({palace.palace_name for palace in chart.palaces}) == 12
    assert {palace.earthly_branch for palace in chart.palaces} == set(BRANCH_GRID_POSITIONS)
    assert sum(len(_star_display_items(chart, palace, major=True)) for palace in chart.palaces) == 14
    assert sum(len(_star_display_items(chart, palace, major=False)) for palace in chart.palaces) == 14


def test_a_render_hierarchy_keeps_required_locations_and_inline_transformations() -> None:
    chart = calculate_basic_chart(birth_data("A"))
    palaces = {palace.earthly_branch: palace for palace in chart.palaces}

    assert (palaces["寅"].palace_name.value, palaces["寅"].palace_ganzhi.display) == ("命宮", "戊寅")
    assert _star_display_items(chart, palaces["寅"], major=True) == ("武曲", "天相")
    assert _star_display_items(chart, palaces["寅"], major=False) == ("陀羅",)

    expected = {
        "巳": ("田宅宮", "辛巳", ("天機【祿】",)),
        "卯": ("父母宮", "己卯", ("太陽", "天梁【權】")),
        "午": ("官祿宮", "壬午", ("紫微【科】",)),
        "亥": ("子女宮", "丁亥", ("太陰【忌】",)),
    }
    for branch, (name, ganzhi, major_stars) in expected.items():
        palace = palaces[branch]
        assert (palace.palace_name.value, palace.palace_ganzhi.display) == (name, ganzhi)
        assert _star_display_items(chart, palace, major=True) == major_stars


def test_renderer_has_real_chinese_font() -> None:
    assert find_chinese_font().is_file()
    assert find_chinese_font(bold=True).is_file()


def test_l_render_preserves_leap_month_and_effective_month(tmp_path: Path) -> None:
    chart = calculate_basic_chart(birth_data("L"))
    artifact = render_chart_png(chart, tmp_path)
    details = dict(_center_details(chart))
    assert_png(artifact.path)
    assert chart.calendar.lunar_date.month == 6
    assert chart.calendar.lunar_date.is_leap_month is True
    assert chart.palace_layout.effective_lunar_month == 7
    assert details["農曆日期"] == "2025 年 閏六月初一"
    assert details["實際農曆月"] == "6"
    assert details["閏月"] == "是"
    assert details["有效本命月"] == "7"


def test_l_render_preserves_adopted_left_right_assistants(tmp_path: Path) -> None:
    chart = calculate_basic_chart(birth_data("L"))
    render_chart_png(chart, tmp_path)
    placements = chart.auxiliary_star_chart.star_to_branch
    assert placements["左輔"] == "戌"
    assert placements["右弼"] == "辰"


def test_z_render_preserves_late_zi_policy(tmp_path: Path) -> None:
    chart = calculate_basic_chart(birth_data("Z"))
    artifact = render_chart_png(chart, tmp_path)
    details = dict(_center_details(chart))
    assert_png(artifact.path)
    assert chart.calendar.solar_date.isoformat() == "2025-07-24"
    assert chart.calendar.lunar_date.month == 6
    assert chart.calendar.lunar_date.day == 30
    assert chart.hour_ganzhi.earthly_branch == "子"
    assert details["西元日期"] == "2025-07-24"
    assert details["時干支"].endswith("子")


def test_png_api_returns_rendered_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    actual_renderer = render_chart_png
    monkeypatch.setattr(chart_api, "render_chart_png", lambda chart: actual_renderer(chart, tmp_path))
    response = client.post("/api/chart/png", json=birth_data("A").model_dump(mode="json"))
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert "attachment" in response.headers["content-disposition"]


def test_png_api_rejects_invalid_input() -> None:
    payload = birth_data("A").model_dump(mode="json")
    payload["birth_hour"] = 24
    assert client.post("/api/chart/png", json=payload).status_code == 422


def test_structured_chart_api_remains_available() -> None:
    response = client.post("/api/chart", json=birth_data("A").model_dump(mode="json"))
    assert response.status_code == 200
    assert len(response.json()["palaces"]) == 12


def test_ziwei_page_keeps_tables_and_adds_png_preview() -> None:
    response = client.get("/ziwei")
    assert response.status_code == 200
    assert 'id="chart-image"' in response.text
    assert 'id="chart-download"' in response.text
    assert 'id="chart-fullsize"' in response.text
    assert 'id="chart-image-link"' in response.text
    assert "放大查看" in response.text
    assert "十二宮" in response.text
    assert "生年四化明細" in response.text


def test_frontend_calls_png_api_without_external_service() -> None:
    javascript = client.get("/static/ziwei.js").text
    assert 'fetch("/api/chart/png"' in javascript
    assert "NVIDIA" not in javascript
    assert "http://" not in javascript
    assert "https://" not in javascript
