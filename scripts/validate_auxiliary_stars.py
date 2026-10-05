"""Development-only Phase 2A manual package. No Node needed."""

import argparse
import json
import sys
from pathlib import Path

from app.models.ziwei import AuxiliaryStarName
from app.ziwei import calculate_basic_chart
from app.ziwei.palace import effective_lunar_month
from scripts.validate_basic_chart import birth


CASES = (("A", "2025-01-29", 0, 30), ("B", "2025-01-29", 1, 30),
         ("C", "2024-02-29", 12, 0), ("L", "2025-07-25", 12, 0),
         ("Z", "2025-07-24", 23, 59))


def normalize(chart) -> dict:
    auxiliary = chart.auxiliary_star_chart
    return {"lunar_date": chart.lunar_date.model_dump(),
            "year_ganzhi": chart.year_ganzhi.display,
            "hour_branch": chart.hour_ganzhi.earthly_branch,
            "life_body_effective_month": chart.palace_layout.effective_lunar_month,
            "auxiliary_effective_month": effective_lunar_month(chart.lunar_date),
            "status": auxiliary.status,
            "stars": {s.name.value: s.earthly_branch for s in auxiliary.stars},
            "palaces": [{"branch": p.earthly_branch, "palace_name": p.palace_name.value,
                         "major_stars": [s.name.value for s in p.major_stars],
                         "auxiliary_stars": [s.name.value for s in p.auxiliary_stars]}
                        for p in chart.palaces]}


def display(chart) -> str:
    b, lunar = chart.birth_data, chart.lunar_date
    value = normalize(chart)
    lines = [f"出生: {chart.solar_date} {b.birth_hour:02}:{b.birth_minute:02} {b.gender.value} {b.birthplace}",
             f"農曆: {lunar.year}年 {'閏' if lunar.is_leap_month else ''}{lunar.month}月{lunar.day}日",
             f"主要年干支: {value['year_ganzhi']} / 時支: {value['hour_branch']}",
             f"實際農曆月: {lunar.month} / 閏月旗標: {lunar.is_leap_month}",
             f"有效本命月: {value['auxiliary_effective_month']}",
             f"命身宮有效月: {value['life_body_effective_month']}",
             f"輔星有效月: {value['auxiliary_effective_month']}",
             f"輔星計算狀態: {value['status']} (不是人工驗收 PASS)",
             "十四輔星:"]
    for name in AuxiliaryStarName:
        lines.append(f"{name.value}: {value['stars'][name.value]}")
    lines.append("地支 | 宮名 | 主星 | 輔星")
    for p in value["palaces"]:
        lines.append(f"{p['branch']} | {p['palace_name']} | {', '.join(p['major_stars']) or '-'} | "
                     f"{', '.join(p['auxiliary_stars']) or '-'}")
    return "\n".join(lines)


def main() -> None:
    # Windows redirected stdout can default to CP950 while consumers expect
    # UTF-8. Keep the plain `python -m ...` command readable in either runtime.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparison-cases", action="store_true")
    parser.add_argument("--save-report", action="store_true")
    args = parser.parse_args()
    charts = [(label, calculate_basic_chart(birth(solar, hour, minute)))
              for label, solar, hour, minute in CASES]
    if args.comparison_cases:
        print(json.dumps([{"case": label, "input": chart.birth_data.model_dump(mode="json"),
                           "chart": normalize(chart)} for label, chart in charts],
                         ensure_ascii=False, indent=2))
        return
    text = "PHASE 2A-R: USER MANUAL VALIDATION REQUIRED (工具輸出不是人工驗收)\n"
    text += "Tiger-ZiWei adopted natal leap-month convention: 閏月 N → 有效本命月 N+1。\n"
    text += "不得開始 Phase 2B。請核對 A/B/C/L 各14星及分宮，還有 Z 晚子時。\n\n"
    text += "\n\n".join(f"CASE {label}\n{display(chart)}" for label, chart in charts) + "\n"
    if args.save_report:
        path = Path("output/phase2a/manual-validation.txt")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
