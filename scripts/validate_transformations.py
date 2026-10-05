"""Development-only Phase 2B manual validation; no Node is required."""

import argparse
import json
import sys
from pathlib import Path

from app.models.basic_chart import BasicChartResult
from app.ziwei import calculate_basic_chart
from scripts.validate_basic_chart import birth
from tests.transformation_reference import TEN_STEM_TABLE, TYPES


CASES = (
    ("A", "2025-01-29", 0, 30),
    ("B", "2025-01-29", 1, 30),
    ("C", "2024-02-29", 12, 0),
    ("L", "2025-07-25", 12, 0),
    ("Z", "2025-07-24", 23, 59),
)


def normalize(chart: BasicChartResult) -> dict:
    return {
        "lunar_date": chart.lunar_date.model_dump(),
        "year_ganzhi": chart.year_ganzhi.display,
        "year_heavenly_stem": chart.birth_year_transformations.year_heavenly_stem,
        "transformations": [
            {
                "transformation": row.transformation.value,
                "star_name": row.star_name.value,
                "star_category": row.star_category.value,
                "earthly_branch": row.earthly_branch,
                "palace_name": row.palace_name.value,
            }
            for row in chart.birth_year_transformations.transformations
        ],
    }


def display(chart: BasicChartResult) -> str:
    b, lunar = chart.birth_data, chart.lunar_date
    lines = [
        f"出生: {chart.solar_date} {b.birth_hour:02}:{b.birth_minute:02} {b.gender.value} {b.birthplace}",
        f"農曆: {lunar.year}年 {'閏' if lunar.is_leap_month else ''}{lunar.month}月{lunar.day}日",
        f"主要年干支: {chart.year_ganzhi.display}",
        f"生年天干: {chart.birth_year_transformations.year_heavenly_stem}",
        "四化 | 目標星 | 類別 | 地支 | 宮名",
    ]
    for row in chart.birth_year_transformations.transformations:
        lines.append(
            f"{row.transformation.value} | {row.star_name.value} | {row.star_category.value} | "
            f"{row.earthly_branch} | {row.palace_name.value}"
        )
    return "\n".join(lines)


def verified_table() -> str:
    lines = ["FINAL VERIFIED TEN-STEM TABLE", "順序: 化祿 / 化權 / 化科 / 化忌"]
    for stem, stars in TEN_STEM_TABLE.items():
        lines.append(f"{stem}: " + " / ".join(
            f"{transformation}={star}"
            for transformation, star in zip(TYPES, stars, strict=True)
        ))
    return "\n".join(lines)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparison-cases", action="store_true")
    parser.add_argument("--save-report", action="store_true")
    args = parser.parse_args()
    charts = [(label, calculate_basic_chart(birth(solar, hour, minute)))
              for label, solar, hour, minute in CASES]
    if args.comparison_cases:
        print(json.dumps({
            "table": TEN_STEM_TABLE,
            "cases": [
                {"case": label, "input": chart.birth_data.model_dump(mode="json"),
                 "chart": normalize(chart)}
                for label, chart in charts
            ],
        }, ensure_ascii=False, indent=2))
        return
    text = (
        "PHASE 2B: USER MANUAL VALIDATION REQUIRED (工具輸出不是人工驗收)\n"
        "生年四化只使用 Phase 1B 主要年干；不移動星曜，不含解讀。\n"
        "壬干採南陽堂《紫微斗數全書》梁紫府武；左輔讀法列為 EDITION_VARIANT。\n\n"
        + verified_table()
        + "\n\n"
        + "\n\n".join(f"CASE {label}\n{display(chart)}" for label, chart in charts)
        + "\n"
    )
    if args.save_report:
        destination = Path("output/phase2b/manual-validation.txt")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
