"""Development-only JSON/manual display. Run as python -m scripts.validate_basic_chart."""

import argparse
import json
from datetime import date
from pathlib import Path

from app.models.birth import BirthData
from app.models.basic_chart import BasicChartResult
from app.ziwei import calculate_basic_chart


def birth(solar: str, hour: int, minute: int, gender: str = "female") -> BirthData:
    value = date.fromisoformat(solar)
    return BirthData(gender=gender, birthplace="Taipei", birth_year=value.year,
                     birth_month=value.month, birth_day=value.day, birth_hour=hour, birth_minute=minute)


def normalize(chart: BasicChartResult) -> dict:
    """Comparison projection only; no astronomy or astrology formulas."""
    return {
        "lunar_date": chart.lunar_date.model_dump(),
        "year_ganzhi": chart.year_ganzhi.display,
        "life": chart.life_palace_branch, "body": chart.body_palace_branch,
        "body_name": chart.body_palace_name.value,
        "life_ganzhi": chart.five_elements_bureau.life_palace_ganzhi.display,
        "bureau": {"name": chart.five_elements_bureau.bureau_name,
                   "number": chart.five_elements_bureau.bureau_number},
        "palaces": [{"branch": p.earthly_branch, "name": p.palace_name.value,
                     "stem": p.heavenly_stem, "ganzhi": p.palace_ganzhi.display,
                     "body": p.has_body_palace,
                     "stars": sorted(s.name.value for s in p.major_stars)} for p in chart.palaces],
        "stars": {s.name.value: s.earthly_branch for s in chart.major_star_chart.stars},
    }


def display(chart: BasicChartResult) -> str:
    b, lunar = chart.birth_data, chart.lunar_date
    lines = [f"出生: {chart.solar_date} {b.birth_hour:02}:{b.birth_minute:02} {b.gender.value} {b.birthplace}",
             f"農曆: {lunar.year}年 {'閏' if lunar.is_leap_month else ''}{lunar.month}月{lunar.day}日",
             "年/月/日/時干支: " + " / ".join(g.display for g in
                 (chart.year_ganzhi, chart.month_ganzhi, chart.day_ganzhi, chart.hour_ganzhi)),
             f"命宮: {chart.life_palace_branch} ({chart.five_elements_bureau.life_palace_ganzhi.display})",
             f"身宮: {chart.body_palace_branch} / {chart.body_palace_name.value}",
             f"五行局: {chart.five_elements_bureau.bureau_name}",
             "地支 | 宮名 | 宮干支 | 身宮 | 十四主星"]
    for p in chart.palaces:
        lines.append(f"{p.earthly_branch} | {p.palace_name.value} | {p.palace_ganzhi.display} | "
                     f"{'是' if p.has_body_palace else '-'} | " +
                     (", ".join(s.name.value for s in p.major_stars) or "-"))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default="2025-01-29")
    parser.add_argument("--hour", type=int, default=0)
    parser.add_argument("--minute", type=int, default=30)
    parser.add_argument("--gender", choices=["male", "female"], default="female")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--comparison-cases", action="store_true")
    parser.add_argument("--manual-package", action="store_true")
    parser.add_argument("--save-report", action="store_true")
    args = parser.parse_args()
    if args.manual_package:
        report_path = Path("output/phase1f/iztro-comparison.json")
        external = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else None
        sections = ["PHASE 1F: USER MANUAL VALIDATION REQUIRED\n"
                    "Automated checks do not constitute user acceptance. No Phase 2 authorization.\n"
                    "All cases: supplied civil time; synthetic female/Taipei input.\n"
                    "Check lunar date, year Ganzhi, Life/Body, every palace name/stem, bureau and all 14 stars."]
        for solar,hour,minute in [("2025-01-29",0,30),("2025-01-29",1,30),("2024-02-29",12,0),("2025-07-25",12,0)]:
            b = birth(solar,hour,minute)
            chart = calculate_basic_chart(b)
            result = next((r for r in external["results"] if r["input"] == b.model_dump(mode="json")),None) if external else None
            status = result["classification"] if result else "INCONCLUSIVE (external report absent)"
            section = display(chart) + "\niztro normalized comparison: " + status
            if chart.lunar_date.is_leap_month:
                section += "\nTiger uses the next month for the WHOLE leap month; iztro fixLeap=true splits at day 15."
                if result:
                    e = result["external"]
                    section += f"\niztro: Life {e['life']}, Body {e['body']}, {e['bureau']['name']}, 紫微 {e['stars']['紫微']}, 天府 {e['stars']['天府']}"
            sections.append(section)
        output = "\n\n".join(sections) + "\n"
        if args.save_report:
            destination = Path("output/phase1f/manual-validation.txt")
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_text(output,encoding="utf-8")
        print(output)
    elif args.comparison_cases:
        from tests.basic_chart_reference import COMPARISON_INPUTS
        results = []
        for solar, hour, minute in COMPARISON_INPUTS:
            b = birth(solar, hour, minute, args.gender)
            results.append({"input": b.model_dump(mode="json"),
                            "chart": normalize(calculate_basic_chart(b))})
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        chart = calculate_basic_chart(birth(args.date, args.hour, args.minute, args.gender))
        print(json.dumps(normalize(chart), ensure_ascii=False, indent=2) if args.json else display(chart))


if __name__ == "__main__":
    main()
