"""Deterministic Pillow renderer for the verified Tiger-ZiWei basic chart."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
import os
from pathlib import Path
import re
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

from app.models.basic_chart import BasicChartPalace, BasicChartResult


CANVAS_SIZE = 1648
MARGIN = 24
CELL_SIZE = 400
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output" / "charts"

# Traditional square arrangement, clockwise from 子 along the outer ring.
BRANCH_GRID_POSITIONS: dict[str, tuple[int, int]] = {
    "巳": (0, 0), "午": (1, 0), "未": (2, 0), "申": (3, 0),
    "辰": (0, 1), "酉": (3, 1), "卯": (0, 2), "戌": (3, 2),
    "寅": (0, 3), "丑": (1, 3), "子": (2, 3), "亥": (3, 3),
}

CENTER_SECTION_TITLES = ("基本資料", "曆法", "命盤", "月規則", "生年四化")
TRANSFORMATION_BADGES = {"化祿": "祿", "化權": "權", "化科": "科", "化忌": "忌"}


@dataclass(frozen=True)
class RenderedChart:
    """Receipt for one written chart image."""

    path: Path
    filename: str
    width: int = CANVAS_SIZE
    height: int = CANVAS_SIZE


@lru_cache(maxsize=2)
def find_chinese_font(*, bold: bool = False) -> Path:
    """Find a usable Chinese font, preferring Traditional Chinese families."""

    configured = os.environ.get("TIGER_ZIWEI_FONT")
    windows = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    candidates = [
        Path(configured) if configured else None,
        windows / ("msjhbd.ttc" if bold else "msjh.ttc"),
        windows / "mingliu.ttc",
        windows / "kaiu.ttf",
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"),
    ]
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return candidate
    raise RuntimeError(
        "找不到可用的中文字型。請安裝 Microsoft JhengHei、MingLiU 或 "
        "Noto Sans CJK TC，或設定 TIGER_ZIWEI_FONT。"
    )


@lru_cache(maxsize=16)
def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(find_chinese_font(bold=bold)), size=size)


def _lunar_month_name(month: int) -> str:
    return ("", "正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "臘")[month]


def _lunar_day_name(day: int) -> str:
    names = (
        "", "初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
        "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
        "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十",
    )
    return names[day]


def _lunar_text(chart: BasicChartResult) -> str:
    lunar = chart.calendar.lunar_date
    leap = "閏" if lunar.is_leap_month else ""
    return f"{lunar.year} 年 {leap}{_lunar_month_name(lunar.month)}月{_lunar_day_name(lunar.day)}"


def _gender_text(chart: BasicChartResult) -> str:
    return "女" if chart.birth_data.gender.value == "female" else "男"


def _filename(chart: BasicChartResult) -> str:
    birth = chart.birth_data
    if birth.name:
        base = birth.name.strip()
    else:
        base = f"{birth.birth_year:04d}-{birth.birth_month:02d}-{birth.birth_day:02d}_{birth.birth_hour:02d}{birth.birth_minute:02d}"
    safe = re.sub(r"[^\w\-㐀-鿿]+", "_", base, flags=re.UNICODE).strip("_")
    return f"{safe or 'Tiger-ZiWei'}_紫微命盤.png"


def _joined_lines(
    draw: ImageDraw.ImageDraw,
    items: Iterable[str],
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    values = list(items)
    if not values:
        return ["—"]
    lines: list[str] = []
    current = ""
    for value in values:
        candidate = value if not current else f"{current}、{value}"
        if current and draw.textlength(candidate, font=font) > max_width:
            lines.append(current)
            current = value
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _star_display_items(
    chart: BasicChartResult,
    palace: BasicChartPalace,
    *,
    major: bool,
) -> tuple[str, ...]:
    """Attach compact Four Transformation markers to their existing stars."""

    changes = {
        item.star_name.value: TRANSFORMATION_BADGES[item.transformation.value]
        for item in chart.birth_year_transformations.transformations
        if item.earthly_branch == palace.earthly_branch
    }
    stars = palace.major_stars if major else palace.auxiliary_stars
    return tuple(
        f"{star.name.value}【{changes[star.name.value]}】" if star.name.value in changes else star.name.value
        for star in stars
    )


def _draw_palace(
    draw: ImageDraw.ImageDraw,
    palace: BasicChartPalace,
    chart: BasicChartResult,
    box: tuple[int, int, int, int],
    fonts: dict[str, ImageFont.FreeTypeFont],
) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=12, fill="#fffdf7", outline="#7d342d", width=3)
    pad = 16
    x = x0 + pad
    y = y0 + 12
    inner_width = x1 - x0 - pad * 2

    draw.text((x, y), palace.palace_name.value, font=fonts["palace"], fill="#6f211d")
    branch_text = f"{palace.heavenly_stem}{palace.earthly_branch}"
    branch_width = draw.textlength(branch_text, font=fonts["palace"])
    draw.text((x1 - pad - branch_width, y), branch_text, font=fonts["palace"], fill="#302724")
    y += 49

    markers: list[str] = []
    if palace.is_life_palace:
        markers.append("【命】")
    if palace.has_body_palace:
        markers.append("【身】")
    if markers:
        draw.text((x, y), " ".join(markers), font=fonts["marker"], fill="#a33b2f")
    y = y0 + 107

    sections: tuple[tuple[str, tuple[str, ...], str, str, int], ...] = (
        ("主星", _star_display_items(chart, palace, major=True), "major", "#24201e", 38),
        ("輔星", _star_display_items(chart, palace, major=False), "auxiliary", "#514b47", 32),
    )
    for label, values, font_key, color, line_height in sections:
        draw.text((x, y), label, font=fonts["label"], fill="#8b776b")
        y += 27
        lines = _joined_lines(draw, values, fonts[font_key], inner_width)
        for line in lines:
            draw.text((x, y), line, font=fonts[font_key], fill=color)
            y += line_height
        y += 13


def _center_details(chart: BasicChartResult) -> tuple[tuple[str, str], ...]:
    """Build display-only center fields directly from the verified result."""

    birth = chart.birth_data
    lunar = chart.calendar.lunar_date
    return (
        ("姓名", birth.name or "未填寫"),
        ("性別", _gender_text(chart)),
        ("西元日期", chart.calendar.solar_date.isoformat()),
        ("出生時間", f"{birth.birth_hour:02d}:{birth.birth_minute:02d}"),
        ("出生地", birth.birthplace),
        ("農曆日期", _lunar_text(chart)),
        ("年干支", chart.year_ganzhi.display),
        ("月干支", chart.month_ganzhi.display),
        ("日干支", chart.day_ganzhi.display),
        ("時干支", chart.hour_ganzhi.display),
        ("命宮", chart.life_palace_branch),
        ("身宮", chart.body_palace_branch),
        ("身宮宿宮", chart.body_palace_name.value),
        ("五行局", chart.five_elements_bureau.bureau_name),
        ("實際農曆月", str(lunar.month)),
        ("閏月", "是" if lunar.is_leap_month else "否"),
        ("有效本命月", str(chart.palace_layout.effective_lunar_month)),
    )


def _draw_center(
    draw: ImageDraw.ImageDraw,
    chart: BasicChartResult,
    box: tuple[int, int, int, int],
    fonts: dict[str, ImageFont.FreeTypeFont],
) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=14, fill="#f8f0df", outline="#7d342d", width=4)
    title = "Tiger-ZiWei 紫微命盤"
    title_width = draw.textlength(title, font=fonts["title"])
    draw.text(((x0 + x1 - title_width) / 2, y0 + 24), title, font=fonts["title"], fill="#6f211d")
    draw.line((x0 + 28, y0 + 88, x1 - 28, y0 + 88), fill="#bd9b61", width=2)

    details = dict(_center_details(chart))
    left_x = x0 + 30
    right_x = x0 + 414

    def draw_group(title_text: str, fields: tuple[str, ...], x: int, y: int) -> int:
        draw.text((x, y), title_text, font=fonts["subhead"], fill="#6f211d")
        y += 37
        for label in fields:
            draw.text((x, y), f"{label}：", font=fonts["center_label"], fill="#7b5e4d")
            label_width = draw.textlength(f"{label}：", font=fonts["center_label"])
            draw.text((x + label_width, y), details[label], font=fonts["center"], fill="#28211f")
            y += 36
        return y

    draw_group("基本資料", ("姓名", "性別", "西元日期", "出生時間", "出生地"), left_x, y0 + 108)
    draw_group("曆法", ("農曆日期", "年干支", "月干支", "日干支", "時干支"), right_x, y0 + 108)
    draw.line((x0 + 28, y0 + 338, x1 - 28, y0 + 338), fill="#d5bd91", width=2)
    chart_end = draw_group("命盤", ("命宮", "身宮", "身宮宿宮", "五行局"), left_x, y0 + 354)
    draw_group("月規則", ("實際農曆月", "閏月", "有效本命月"), left_x, chart_end + 10)

    transform_y = y0 + 354
    draw.text((right_x, transform_y), "生年四化", font=fonts["subhead"], fill="#6f211d")
    transform_y += 42
    for item in chart.birth_year_transformations.transformations:
        category = "主星" if item.star_category.value == "major" else "輔星"
        text = f"{item.transformation.value}　{item.star_name.value}【{category}】"
        draw.text((right_x, transform_y), text, font=fonts["center"], fill="#28211f")
        draw.text((right_x + 230, transform_y), f"{item.earthly_branch}・{item.palace_name.value}", font=fonts["center_meta"], fill="#765f54")
        transform_y += 43

    footer = "本圖僅呈現已驗證排盤資料｜不含解讀｜LLM 不參與排盤"
    footer_width = draw.textlength(footer, font=fonts["footer"])
    draw.text(((x0 + x1 - footer_width) / 2, y1 - 48), footer, font=fonts["footer"], fill="#756b63")


def render_chart_png(
    chart: BasicChartResult,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> RenderedChart:
    """Render an existing verified chart into a deterministic PNG file."""

    fonts = {
        "title": _font(42, bold=True),
        "palace": _font(34, bold=True),
        "marker": _font(24, bold=True),
        "label": _font(19),
        "major": _font(30, bold=True),
        "auxiliary": _font(24),
        "center_label": _font(20, bold=True),
        "center": _font(24),
        "center_meta": _font(20),
        "subhead": _font(26, bold=True),
        "footer": _font(18),
    }
    image = Image.new("RGB", (CANVAS_SIZE, CANVAS_SIZE), "#eee4d2")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (10, 10, CANVAS_SIZE - 10, CANVAS_SIZE - 10),
        radius=20,
        fill="#f4ecdc",
        outline="#5e2925",
        width=5,
    )

    palace_by_branch = {palace.earthly_branch: palace for palace in chart.palaces}
    for branch, (column, row) in BRANCH_GRID_POSITIONS.items():
        x0 = MARGIN + column * CELL_SIZE
        y0 = MARGIN + row * CELL_SIZE
        _draw_palace(draw, palace_by_branch[branch], chart, (x0, y0, x0 + CELL_SIZE, y0 + CELL_SIZE), fonts)

    center_box = (
        MARGIN + CELL_SIZE,
        MARGIN + CELL_SIZE,
        MARGIN + CELL_SIZE * 3,
        MARGIN + CELL_SIZE * 3,
    )
    _draw_center(draw, chart, center_box, fonts)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    filename = _filename(chart)
    destination = output_path / filename
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Title", "Tiger-ZiWei 紫微命盤")
    metadata.add_text("Generator", "Tiger-ZiWei deterministic renderer")
    buffer = BytesIO()
    image.save(buffer, format="PNG", pnginfo=metadata)
    destination.write_bytes(buffer.getvalue())
    return RenderedChart(path=destination, filename=filename)
