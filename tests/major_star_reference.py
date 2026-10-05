"""Static classical oracle, transcribed by palace cell, NOT from an algorithm.

Reviewed 2026-10-05, Quan Shu vol.2, Wikisource revision 1963110:
https://zh.wikisource.org/zh-hant/紫微斗數全書/卷二
Five bureau charts following 官府主官符, before 安天府圖.

Two source defects are preserved in RAW_CLASSICAL_CELLS:
  木三局: 寅 cell reads 初三/初九, duplicating 初九 in 辰 and omitting 初五.
  金四局: 亥 cell lists only 初一, omitting 三十.
Resolution BEFORE running production: CUST lecture 18, printed/PDF page 4
visually gives 木 day 5 寅, day 9 辰, and 金 day 30 亥. These also agree with
the specified padding rule and iztro getStartIndex. See README audit.
https://cc.cust.edu.tw/~wtcbee/index.files/teaching/98-2/Geomancy2/lesson/18.pdf
PDF SHA256: 620744696eea870dca9008605af4b6a01c5aee02248e170e6671413cc7312e86

The accepted static cells below incorporate only these explicit resolutions.
No imports from production and no position-generating formula belong here.
"""

CLASSICAL_CELLS = {
    2: {
        "巳": (8, 9), "午": (10, 11), "未": (12, 13), "申": (14, 15),
        "辰": (6, 7, 30), "酉": (16, 17), "卯": (4, 5, 28, 29), "戌": (18, 19),
        "寅": (2, 3, 26, 27), "丑": (1, 24, 25), "子": (22, 23), "亥": (20, 21),
    },
    3: {
        "巳": (4, 12, 14), "午": (7, 15, 17), "未": (10, 18, 20), "申": (13, 21, 23),
        "辰": (1, 9, 11), "酉": (16, 24, 26), "卯": (6, 8), "戌": (19, 27, 29),
        "寅": (3, 5), "丑": (2, 28), "子": (25,), "亥": (22, 30),
    },
    4: {
        "巳": (6, 16, 19, 25), "午": (10, 20, 23, 29), "未": (14, 24, 27), "申": (18, 28),
        "辰": (2, 12, 15, 21), "酉": (22,), "卯": (8, 11, 17), "戌": (26,),
        "寅": (4, 7, 13), "丑": (3, 9), "子": (5,), "亥": (1, 30),
    },
    5: {
        "巳": (8, 20, 24), "午": (1, 13, 25, 29), "未": (6, 18, 30), "申": (11, 23),
        "辰": (3, 15, 19, 27), "酉": (16, 28), "卯": (10, 14, 22), "戌": (21,),
        "寅": (5, 9, 17), "丑": (4, 12), "子": (7,), "亥": (2, 26),
    },
    6: {
        "巳": (10, 24, 29), "午": (2, 16, 30), "未": (8, 22), "申": (14, 28),
        "辰": (4, 18, 23), "酉": (1, 20), "卯": (12, 17, 27), "戌": (7, 26),
        "寅": (6, 11, 21), "丑": (5, 15, 25), "子": (9, 19), "亥": (3, 13),
    },
}
RAW_CLASSICAL_CELLS = {b: dict(cells) for b, cells in CLASSICAL_CELLS.items()}
RAW_CLASSICAL_CELLS[3]["寅"] = (3, 9)
RAW_CLASSICAL_CELLS[4]["亥"] = (1,)

# This inversion just indexes the fixed transcribed cells; it calculates no
# expected placement from a bureau/day algorithm.
CLASSICAL_CASES = tuple((bureau, day, branch)
                        for bureau, cells in CLASSICAL_CELLS.items()
                        for branch, days in cells.items() for day in days)

TIANFU_REFERENCE = {
    "子": "辰", "丑": "卯", "寅": "寅", "卯": "丑", "辰": "子", "巳": "亥",
    "午": "戌", "未": "酉", "申": "申", "酉": "未", "戌": "午", "亥": "巳",
}
STAR_NAMES = ("紫微", "天機", "太陽", "武曲", "天同", "廉貞",
              "天府", "太陰", "貪狼", "巨門", "天相", "天梁", "七殺", "破軍")

# Fully hand-specified relative pattern for each possible 紫微 start. Columns
# follow STAR_NAMES; derived from the classical star sequence and 天府圖,
# NOT imported production helpers or output. Includes all human checkpoints.
FULL_LAYOUTS = {
    "子": "子亥酉申未辰辰巳午未申酉戌寅",
    "丑": "丑子戌酉申巳卯辰巳午未申酉丑",
    "寅": "寅丑亥戌酉午寅卯辰巳午未申子",
    "卯": "卯寅子亥戌未丑寅卯辰巳午未亥",
    "辰": "辰卯丑子亥申子丑寅卯辰巳午戌",
    "巳": "巳辰寅丑子酉亥子丑寅卯辰巳酉",
    "午": "午巳卯寅丑戌戌亥子丑寅卯辰申",
    "未": "未午辰卯寅亥酉戌亥子丑寅卯未",
    "申": "申未巳辰卯子申酉戌亥子丑寅午",
    "酉": "酉申午巳辰丑未申酉戌亥子丑巳",
    "戌": "戌酉未午巳寅午未申酉戌亥子辰",
    "亥": "亥戌申未午卯巳午未申酉戌亥卯",
}

WOOD_27 = {
    "紫微": "戌", "天機": "酉", "太陽": "未", "武曲": "午", "天同": "巳", "廉貞": "寅",
    "天府": "午", "太陰": "未", "貪狼": "申", "巨門": "酉", "天相": "戌", "天梁": "亥",
    "七殺": "子", "破軍": "辰",
}
JAN29_MIDNIGHT = {
    "紫微": "午", "天機": "巳", "太陽": "卯", "武曲": "寅", "天同": "丑", "廉貞": "戌",
    "天府": "戌", "太陰": "亥", "貪狼": "子", "巨門": "丑", "天相": "寅", "天梁": "卯",
    "七殺": "辰", "破軍": "申",
}
