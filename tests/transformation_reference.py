"""Hand-reviewed Phase 2B fixtures; no production table is imported here.

Order in each four-name row is 化祿、化權、化科、化忌. The 壬 row follows
the selected 南陽堂《紫微斗數全書》 edition; the 左輔 row is separately
recorded as an edition variant in the Phase 2B documentation.
"""

TYPES = ("化祿", "化權", "化科", "化忌")

TEN_STEM_TABLE = {
    "甲": ("廉貞", "破軍", "武曲", "太陽"),
    "乙": ("天機", "天梁", "紫微", "太陰"),
    "丙": ("天同", "天機", "文昌", "廉貞"),
    "丁": ("太陰", "天同", "天機", "巨門"),
    "戊": ("貪狼", "太陰", "右弼", "天機"),
    "己": ("武曲", "貪狼", "天梁", "文曲"),
    "庚": ("太陽", "武曲", "太陰", "天同"),
    "辛": ("巨門", "太陽", "文曲", "文昌"),
    "壬": ("天梁", "紫微", "天府", "武曲"),
    "癸": ("破軍", "巨門", "太陰", "貪狼"),
}

FORTY_ASSIGNMENTS = tuple(
    (stem, transformation, star)
    for stem, stars in TEN_STEM_TABLE.items()
    for transformation, star in zip(TYPES, stars, strict=True)
)

# Record = transformation, target, category, branch, palace.
INTEGRATION_CASES = {
    "A": {
        "input": ("2025-01-29", 0, 30), "year": "乙巳",
        "records": (
            ("化祿", "天機", "major", "巳", "田宅宮"),
            ("化權", "天梁", "major", "卯", "父母宮"),
            ("化科", "紫微", "major", "午", "官祿宮"),
            ("化忌", "太陰", "major", "亥", "子女宮"),
        ),
    },
    "B": {
        "input": ("2025-01-29", 1, 30), "year": "乙巳",
        "records": (
            ("化祿", "天機", "major", "申", "疾厄宮"),
            ("化權", "天梁", "major", "子", "兄弟宮"),
            ("化科", "紫微", "major", "酉", "財帛宮"),
            ("化忌", "太陰", "major", "申", "疾厄宮"),
        ),
    },
    "C": {
        "input": ("2024-02-29", 12, 0), "year": "甲辰",
        "records": (
            ("化祿", "廉貞", "major", "戌", "福德宮"),
            ("化權", "破軍", "major", "申", "命宮"),
            ("化科", "武曲", "major", "寅", "遷移宮"),
            ("化忌", "太陽", "major", "卯", "疾厄宮"),
        ),
    },
    "L": {
        "input": ("2025-07-25", 12, 0), "year": "乙巳",
        "records": (
            ("化祿", "天機", "major", "巳", "田宅宮"),
            ("化權", "天梁", "major", "卯", "父母宮"),
            ("化科", "紫微", "major", "午", "官祿宮"),
            ("化忌", "太陰", "major", "亥", "子女宮"),
        ),
    },
    "Z": {
        "input": ("2025-07-24", 23, 59), "year": "乙巳",
        "records": (
            ("化祿", "天機", "major", "戌", "田宅宮"),
            ("化權", "天梁", "major", "戌", "田宅宮"),
            ("化科", "紫微", "major", "亥", "官祿宮"),
            ("化忌", "太陰", "major", "午", "兄弟宮"),
        ),
    },
}
