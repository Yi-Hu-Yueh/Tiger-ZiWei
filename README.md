# Tiger-ZiWei

Tiger-ZiWei is being built with a strict separation between:

1. deterministic Zi Wei Dou Shu chart calculation; and
2. LLM-based interpretation of an already calculated chart.

The LLM is never allowed to calculate the Zi Wei chart.

## Scope

Phase 1A supplies the project skeleton, validated Gregorian `BirthData`, and
FastAPI health endpoint. Phase 1A contains no Zi Wei chart calculation rules.
Phase 1B adds deterministic Gregorian/lunar conversion, explicit leap months,
reverse conversion, and structured year/month/day/hour Ganzhi using `sxtwl==2.0.7`.
The LLM performs no calendar calculation.

Phase 1C adds Life/Body Palaces, twelve-palace placement, and the Body Palace host.
Phase 1D adds palace Heavenly Stems, Life Palace Ganzhi, Na Yin, and Five Elements
Bureau. Phase 1E adds deterministic placement of the Fourteen Major Stars.
Phase 1F composes that verified core. Phase 2A adds fourteen auxiliary-star
rules and separate palace grouping. Phase 2A-R explicitly applies the adopted
natal leap-month convention to 左輔/右弼; all supported results have 14 stars.
The Phase 2A user manual gate remains REQUIRED; see the source/gate audit below.
Phase 2B adds only deterministic **birth-year** Four Transformations, selected
from Phase 1B's primary Lunar-New-Year stem and attached to existing stars.
Its user manual gate remains REQUIRED. Palace-stem, luck-period, annual and
self/flying transformations remain **NOT IMPLEMENTED**, as do brightness,
other miscellaneous stars, and luck cycles.
PNG charts, NVIDIA/LLM integration, and DOCX reports are **NOT IMPLEMENTED**.
Passing these phase tests does not establish full Zi Wei chart correctness.

## Calendar conventions

- `lunar_date` contains year, month, day, and a required `is_leap_month` flag.
  Conversion uses sxtwl's deterministic astronomy; no website is called at runtime.
- Primary `year_ganzhi` uses **Lunar New Year**, explicitly calling
  `getYearGZ(True)`. It does not use the library's default Li Chun boundary.
- `month_ganzhi` is separate from `lunar_date.month`. The former follows the
  twelve solar-term **dates** (Jie) in `getMonthGZ()`. It changes at midnight
  starting the term's civil date, not at the astronomical instant. For example,
  CWA lists Li Chun at 2025-02-03 22:10 (UTC+08), while the engine returns
  戊寅 for that entire date. Exact-instant Four-Pillars month calculation is
  **NOT IMPLEMENTED**. Future Zi Wei month rules must use `lunar_date.month`
  and its leap flag, never infer the lunar month from `month_ganzhi`.
- `day_ganzhi` and the lunar date preserve the supplied Gregorian civil date;
  they change at civil midnight, not 23:00.
- Birth time uses supplied **civil/standard clock time**. Minutes are retained;
  hour Ganzhi periods change at whole-hour boundaries (子 23:00-00:59,
  丑 01:00-02:59, 午 11:00-12:59, 亥 21:00-22:59).
- Hour calculation explicitly calls `getHourGZ(hour, False)` to pair each
  period with the current civil day's stem, including 23:00. The engine's
  default `True` returns a different 23:00 stem, without changing its day
  object. Both behaviors are regression-tested and distinguished below.
- **No Zi Wei school-specific late-Zi day-boundary convention has been adopted.**
  Phase 1C uses the unchanged lunar month and 子 hour at 23:xx. A later phase
  that needs lunar-day rules must decide its day-boundary convention explicitly.
- True solar time, longitude correction, Equation of Time, timezone lookup,
  and DST adjustments are **NOT IMPLEMENTED**. Birthplace is not geocoded.
  The underlying Chinese lunar calendar uses UTC+08 calendar dates; supplied
  dates are not converted from another timezone. Overseas birth interpretation
  will need an explicit policy in a later phase.

`CalendarResult` carries machine-readable time, year, month, day, and hour
policy indicators alongside the supplied date/time and four separate Ganzhi
objects. Each Ganzhi contains validated Chinese stem/branch characters.

### Late-night behavior

| Supplied civil time | Lunar date | Day Ganzhi | Project hour Ganzhi | Raw engine default hour |
| --- | --- | --- | --- | --- |
| 2025-01-29 00:00 | 2025-01-01 | 戊戌 | 壬子 | 壬子 |
| 2025-01-29 22:59 | 2025-01-01 | 戊戌 | 癸亥 | 癸亥 |
| 2025-01-29 23:00 | 2025-01-01 | 戊戌 | 壬子 | 甲子 |
| 2025-01-29 23:59 | 2025-01-01 | 戊戌 | 壬子 | 甲子 |
| 2025-01-30 00:00 | 2025-01-02 | 己亥 | 甲子 | 甲子 |

### Range and reliability

`BirthData` retains Phase 1A's standard-library Gregorian validation. Conversion
rejects dates earlier than **1582-10-15** because sxtwl's solar API uses the
historical Julian/Gregorian cutover (1582-10-04 is followed by 1582-10-15).
This guards against silently interpreting proleptic Gregorian input as Julian;
it is not a Zi Wei supported-year claim. Python's date representation ends at
9999-12-31; acceptance within that range is not an independent accuracy guarantee.
The official reference vectors exercised here concern 2024-2025. The cutover
test establishes adapter behavior only, not historical lunar accuracy.

Reverse conversion rejects nonexistent leap months and days exceeding the
library's actual lunar month length, then checks that the requested date survives
conversion. Round trips supplement, but do not replace, independent references.

## Independent validation sources

All sources were reviewed on 2026-10-05. Tests keep explicit expected values
and require neither downloads nor network access.

1. [Taiwan CWA 2025 astronomical almanac](https://www.cwa.gov.tw/Data/service/notice/download/Publish_20241209150048.pdf):
   printed p.170 / PDF p.175 supplies 2023-2025 lunar month starts and lengths,
   including 2025-07-25 = leap sixth month day 1. Printed p.12 / PDF p.17 gives
   January 28-30 lunar dates and year/day Ganzhi. Printed p.6 / PDF p.11 gives
   the independent day method: 2025-01-01 JDN = 2460677, position =
   `(JDN - 10) % 60` in a one-based cycle (zero means position 60).
   Test-only Python date differences extend this anchor to other vectors.
   Printed p.4 / PDF p.9 gives the Li Chun date/time.
   This published almanac was used instead of an authenticated A0087-001 feed.
   Download SHA-256:
   `5ae441dcf0ff44c1ef6655f5ad011994f938335f0d54361c2bf579654490b1da`.
2. [HKO 2024 correspondence table](https://www.hko.gov.hk/tc/gts/time/calendar/text/files/T2024c.txt)
   and [HKO 2025 correspondence table](https://www.hko.gov.hk/tc/gts/time/calendar/text/files/T2025c.txt):
   independent cross-checks for Lunar New Year, Gregorian leap day, and leap June.
3. [HKO Heavenly Stems and Earthly Branches](https://www.hko.gov.hk/tc/gts/time/stemsandbranches.htm):
   tables 3 and 5 establish hour periods and stems from independently verified
   day stems. Table 4, combined with CWA's Li Chun boundary and the documented
   engine month convention, establishes 丁丑 before and 戊寅 after the 2025 boundary.
   The boundary reference test uses times clearly outside the exact transition;
   a separate engine-behavior test records midnight granularity. It does not
   claim that midnight is the authoritative astronomical transition.
4. [Taiwan Ministry of the Interior year table](https://www.ris.gov.tw/documents/html/8/1/219.html)
   cross-checks the lunar year names 癸卯 (2023), 甲辰 (2024), and 乙巳 (2025).

## Library evaluation

[PyPI sxtwl 2.0.7](https://pypi.org/project/sxtwl/2.0.7/) was the latest stable
release checked. It installed and imported on Windows: a source-built CPython
3.14 wheel and the published CPython 3.11 Windows wheel. Required conversion,
leap-month, year, month, day, and hour APIs were exercised on the installed
package. It was accepted after the external vectors matched.

[Upstream API documentation](https://github.com/yuangu/sxtwl_cpp/blob/master/python/README.md)
and [month/day implementation](https://github.com/yuangu/sxtwl_cpp/blob/master/src/day.cpp)
were reviewed for conventions. Actual installed-version tests, including the
23:00 flag comparison, prevent relying solely on examples or flag names.

## Phase 1C palace rules

Primary source: [紫微斗數全書, volume 2](https://zh.wikisource.org/zh-hant/紫微斗數全書/卷二),
the classical text transcribed in Wikisource, sections **安身命例** and
**安十二宮例** (reviewed 2026-10-05). This is a rule-text reference, not an
undocumented calculator formula or a claim of facsimile edition authentication.
The reviewed page identifies revision `oldid=1963110` (2020-09-04).

- Begin month 1 at 寅 and advance to the effective lunar month. Starting 子 at
  that position, count backwards to the birth-hour branch for Life Palace;
  count forwards for Body Palace.
- Use Phase 1B's `lunar_date.month` and `is_leap_month`, never Gregorian month
  or `month_ganzhi`. The structured `hour_ganzhi.earthly_branch` supplies the
  hour branch without parsing display text.
- The adopted classical rule treats **all days of leap month N as month N+1**.
  Thus 2025 leap June uses effective month 7. There is no day-15 split or
  configurable school. The original lunar date remains unchanged.
- Effective months 1-12 are supported. A leap-twelfth-month input raises an
  explicit `ValueError`; no month-13 rollover or year adjustment is invented.
  Other calendar range restrictions remain those documented for Phase 1B.
- Place the twelve names backwards from Life: 命宮、兄弟宮、夫妻宮、子女宮、
  財帛宮、疾厄宮、遷移宮、交友宮、官祿宮、田宅宮、福德宮、父母宮.
  The classical 妻妾/奴僕 names are represented by 夫妻宮/交友宮.
  僕役宮 means 交友宮 and 事業宮 means 官祿宮 for display; aliases do not
  create additional palace positions.
- Body Palace is exactly one marker attached to an existing palace, never a
  thirteenth palace. Its host is one of 命宮、夫妻宮、財帛宮、遷移宮、官祿宮、福德宮.
- **23:00-23:59 is 子 hour**, without changing Phase 1B's civil date, lunar
  date, or day Ganzhi. True solar time remains **NOT IMPLEMENTED**.

`calculate_palaces(CalendarResult)` returns an immutable `PalaceLayout` with
effective lunar month, birth-hour branch, twelve positions, Life/Body branches,
and explicit Body host name. Summary/marker fields are derived to stay consistent.
`place_palaces(LunarDate, EarthlyBranch)` also permits synthetic rule vectors;
it trusts the supplied lunar date rather than performing another conversion.

### Phase 1C reference checkpoint

The classical explicit vectors are month 1 / 子 -> 寅/寅, 丑 -> 丑/卯, and
寅 -> 子/辰 (Life/Body). Tests transcribe these and the complete Life-at-寅
twelve-palace vector. All 12 hours are checked over 12 normal and 11 supported
leap month inputs (276 layouts) for unique positions and the six legal Body hosts.

The full Gregorian cases below use CWA lunar correspondence (Phase 1B sources
above), then hand-counted classical placements. These expectations are independent
of the function under test; they are **not** external calculator outputs.
All use synthetic female/Taipei birth data and supplied civil clock time.

| Gregorian date/time | Lunar result | Effective month | Expected Life/Body |
| --- | --- | --- | --- |
| 2025-01-29 00:30 | 2025 month 1 day 1 | 1 | 寅 / 寅 |
| 2025-01-29 01:30 | 2025 month 1 day 1 | 1 | 丑 / 卯 |
| 2025-01-29 03:30 | 2025 month 1 day 1 | 1 | 子 / 辰 |
| 2024-02-29 12:00 | 2024 month 1 day 20 | 1 | 申 / 申 |
| 2025-07-25 14:30 | 2025 leap month 6 day 1 | 7 | 丑 / 卯 |
| 2025-07-25 12:00 | 2025 leap month 6 day 1 | 7 | 寅 / 寅 |
| 2025-07-24 23:59 | 2025 month 6 day 30 | 6 | 未 / 未 |
| 2025-07-25 00:00 | 2025 leap month 6 day 1 | 7 | 申 / 申 |

External calculator review on 2026-10-05:

| Source | Source convention / availability | Our convention | Comparison |
| --- | --- | --- | --- |
| [NCC settings](https://fate.ncc.com.tw/trial/setting/Gv), [vendor documentation](https://nccsoft.com/?p=1707) | Offers next-month mode and palace leap-month toggle. Saving aligned settings redirected to login with a subscription-access message. No chart output was obtained. | Whole leap month as N+1; lunar month; civil date retained | **INCONCLUSIVE** external comparison for the cases above: expected values are shown above, external actual values unavailable. |
| [LifeDNA convention](https://www.lifedna.com.tw/blog/c40.html) | Documents days 1-15 as current month, day 16 onward as next month | All leap-month days as next month | **DIFFERENT_CONVENTION**, documentation finding only; no chart agreement/disagreement claimed. |

No subscription or account was created, and no external calculator dependency
was added. The external comparison remains a human checkpoint; automated
classical-rule and CWA integration checks remain independently reproducible.
Phase 1C verification on 2026-10-05: Python 3.11.3 and Python 3.14.7 each
passed the complete suite with **161 passed, 0 failed**, including all 96
Phase 1A/1B tests and 65 new Phase 1C tests. All eight full-input vectors above
matched their expected lunar and Life/Body values. There were no critical
rule/reference mismatches; the external NCC comparison remains INCONCLUSIVE.

## Phase 1D Five Elements Bureau

The deterministic chain is `BirthData -> Phase 1B -> Phase 1C -> Phase 1D`:

- Take **only** Phase 1B's primary `year_ganzhi.heavenly_stem`, using the
  **Lunar New Year** boundary. No Gregorian-year arithmetic, Li Chun year,
  month/day Ganzhi, or current system year is used to select the year stem.
- Five-Tiger / 五虎遁 assigns the 寅 position's stem:
  **甲己 -> 丙; 乙庚 -> 戊; 丙辛 -> 庚; 丁壬 -> 壬; 戊癸 -> 甲**.
- Advance stems through fixed branch positions **寅卯辰巳午未申酉戌亥子丑**,
  wrapping 癸 to 甲. These are branch locations, not Phase 1C's reverse-ordered
  palace names. For 甲/己, the twelve stems are `丙丁戊己庚辛壬癸甲乙丙丁`.
- Reuse Phase 1C's `life_palace_branch` and its assigned stem to construct a
  validated Life Palace `Ganzhi`; **Life Palace is not recalculated** in Phase 1D.
- Look up that pair in an explicit, immutable **60-Jiazi Na Yin table**.
  Na Yin determines the element, not the stem's or branch's own five element.
- Map **水2、木3、金4、土5、火6**, named 水二局、木三局、金四局、土五局、火六局.
  These are Zi Wei bureau numbers, **not ordinary elemental numbering** (e.g.
  水1/火2), nor iztro's intermediate arithmetic indices 木1/金2/水3/火4/土5.

`calculate_five_elements_bureau(calendar_result, palace_layout)` expects results
from the **same birth input**. It consumes their authoritative year stem and Life
branch; it does not revalidate their shared provenance by recalculating palaces.
The frozen `FiveElementsBureauResult` contains the year stem, 寅 stem, structured
Life Ganzhi and Na Yin element. Life stem/branch and bureau name/number are derived
serialized fields; use `model_dump(round_trip=True)` to revalidate a payload.
`palace_heavenly_stems(year_stem)` exposes a fresh branch-keyed twelve-position map.
The low-level `bureau_from_year_stem_and_life_branch` supports explicit rule
vectors without introducing another calendar or Life Palace calculation path.
Invalid Ganzhi characters or parity raise validation errors, never a default局.
The LLM performs **none** of these calculations. No new dependency was added.

### Phase 1D sources and transcription audit

Reviewed 2026-10-05:

1. Primary: [紫微斗數全書, volume 2](https://zh.wikisource.org/zh-hant/紫微斗數全書/卷二),
   **起五行寅例**, **六十花甲子納音歌**, and the five bureau table headings.
   **安身命例** explicitly gives 甲 year + Life 寅 -> 丙寅 -> 爐中火 -> 火局;
   the 火六局 heading supplies number 6. This remains a public transcription,
   not an authenticated facsimile edition claim.
2. Secondary: [iztro, section 12 定五行局訣](https://iztro.com/learn/setup),
   explicitly publishes **丙子 -> 水二局**, **辛未 -> 土五局**, and
   **庚申 -> 木三局**. All three are fixed regressions. Its documented arithmetic
   is also used **only in tests** to independently cross-check every one of
   the 60 table values. Production uses the classical fixed table, not this
   shortcut. iztro is neither installed nor a runtime dependency.
3. The primary transcription has **甲戊** in the 山頭火 row and **已亥** in
   the 平地木 row. Neither is a valid Jiazi. Investigation before implementation
   compared the parallel classical text [淵海子平, 論六十花甲子納音並註解](https://www.donglishuzhai.net/chapter/5650.html),
   which explicitly gives **甲戌/乙亥 = 山頭火** and **戊戌/己亥 = 平地木**.
   The table uses **甲戌 = 火** and **己亥 = 木**, also matching the secondary
   rule and canonical Jiazi. The source discrepancy is thus resolved and recorded,
   not silently copied or adjusted to fit program output. Full Na Yin name
   spelling variants are not public data fields; only the five element is returned.

### Phase 1D validation checkpoint

`tests/test_five_elements.py` keeps a separate literal 60-pair reference fixture,
five complete twelve-position stem sequences, all ten Five-Tiger inputs, all five
bureau vectors, and the three published iztro examples. The raw 30 two-pair table
rows are retained so duplicates cannot be hidden by dictionary overwrites.
Tests require exactly 60 unique canonical Jiazi, valid stem/branch characters,
valid parity and elements, no omissions, and exactly one bureau per result.
Five distinct start patterns x twelve locations must also yield all 60 unique
pairs. Corrupted-table tests exercise duplicates, omissions, invalid characters,
parity, lengths and elements; successful table loading alone is not validation.

The classical/manual expected vectors are 甲 year + 子/寅/辰/午/申 ->
丙子水2 / 丙寅火6 / 戊辰木3 / 庚午土5 / 壬申金4. They are literals, not
expected values generated by the tested functions.

Full-input expectations use the Phase 1B CWA/HKO references and Phase 1C
hand-counted Life placements, then Five-Tiger and Na Yin. All use synthetic
female/Taipei BirthData, with supplied civil time. The first eight repeat the
existing Phase 1C cases; the last two additionally protect the year boundary.

| Gregorian input | Primary year stem | Life | Life Ganzhi | Na Yin | Bureau |
| --- | --- | --- | --- | --- | --- |
| 2025-01-29 00:30 | 乙 | 寅 | 戊寅 | 土 | 土五局 (5) |
| 2025-01-29 01:30 | 乙 | 丑 | 己丑 | 火 | 火六局 (6) |
| 2025-01-29 03:30 | 乙 | 子 | 戊子 | 火 | 火六局 (6) |
| 2024-02-29 12:00 | 甲 | 申 | 壬申 | 金 | 金四局 (4) |
| 2025-07-25 14:30 | 乙 | 丑 | 己丑 | 火 | 火六局 (6) |
| 2025-07-25 12:00 | 乙 | 寅 | 戊寅 | 土 | 土五局 (5) |
| 2025-07-24 23:59 | 乙 | 未 | 癸未 | 木 | 木三局 (3) |
| 2025-07-25 00:00 | 乙 | 申 | 甲申 | 水 | 水二局 (2) |
| 2025-01-28 00:30 | 甲 | 丑 | 丁丑 | 水 | 水二局 (2) |
| 2024-02-09 00:30 | 癸 | 丑 | 乙丑 | 金 | 金四局 (4) |

2025-01-29 is after Lunar New Year but before Li Chun; 2024-02-09 is after
Li Chun but before Lunar New Year. These prevent substituting a Li Chun or
Gregorian year rule. Late-Zi and leap-month integration preserve Phase 1B/1C
policies. Phase 1D itself did not include star placement or claim full-chart
correctness; the subsequent Phase 1E work is documented below.

Phase 1D verification on 2026-10-05:
`.\.venv311\Scripts\python.exe -m pytest -q` with Python **3.11.3**, and
`python -m pytest -q` with Python **3.14.7**, each returned **279 passed, 0 failed**:
the previous 161 tests plus 118 Phase 1D tests. All ten full-input cases and the
manual five-bureau/secondary vectors matched; 60 expected and 60 actual unique
Jiazi, zero missing, duplicate or invalid pairs. No unresolved critical mismatch.
The 3.11 run emitted the existing upstream Starlette/httpx deprecation warning.
Phase 1D status: **PASS** for this scoped rule chain and regression suite only.

## Phase 1E Fourteen Major Stars

`calculate_major_stars(calendar_result.lunar_date, bureau_result)` consumes the
structured Phase 1B `LunarDate` and Phase 1D `FiveElementsBureauResult` from the
same birth input. Only **lunar day (1-30) + bureau (2-6)** affect star placement.
No calendar conversion, Life Palace, Ganzhi, Na Yin or bureau is recalculated.
The caller remains responsible for upstream provenance; Phase 1E revalidates
object structure, not the upstream algorithms. Invalid days, bureau numbers,
objects and branches fail explicitly; values are not silently normalized.

1. For 紫微, find the smallest nonnegative padding `offset` making `day + offset`
   divisible by the bureau number. Let `quotient = (day + offset) // bureau`.
   Count 寅 as position 1, moving forward `quotient - 1` places; then move forward
   by an even offset or backwards by an odd offset, wrapping modulo 12.
   The low-level function returns offset, quotient, base branch and final branch
   so intermediate arithmetic can be verified independently.
2. 天府 reflects 紫微 across the 寅/申 axis; using the shared 子-based branch
   indices this is `(4 - ziwei_index) % 12`. They coincide only at 寅 and 申.
3. 紫微 group: 紫微 0, 天機 -1, 太陽 -3, 武曲 -4, 天同 -5, 廉貞 -8.
4. 天府 group: 天府 0, 太陰 +1, 貪狼 +2, 巨門 +3, 天相 +4, 天梁 +5,
   七殺 +6, 破軍 +10.

All shared outputs use the existing canonical 子丑寅卯辰巳午未申酉戌亥 order.
The immutable `MajorStarChart` contains exactly fourteen unique named records,
the lunar day and bureau element; bureau name/number and 紫微/天府 summaries are
derived. Multiple stars **may share a branch**. Fresh `star_to_branch` and
`branch_to_stars` views preserve these shared positions, including empty branches.
Serialization uses `model_dump()`; revalidation uses `model_dump(round_trip=True)`.

Leap-month responsibility stays in Phases 1B/1C/1D. **23:00-23:59 never advances
the lunar day in Phase 1E**. For 2025-07-24 23:59, day 30 / 木三局 gives 紫微亥,
天府巳. The separately supplied next civil date 2025-07-25 00:00 gives day 1 /
水二局, 紫微丑, 天府卯. Neither input is mutated. No LLM participates.

### Phase 1E sources and exact table audit

Reviewed 2026-10-05:

- Primary: [紫微斗數全書卷二](https://zh.wikisource.org/zh-hant/紫微斗數全書/卷二),
  Wikisource revision `1963110`: the five birthday/bureau charts, 安南北斗諸星訣,
  安天府圖 and 安身命例. This is a transcribed classical text, not authenticated
  facsimile evidence. `tests/major_star_reference.py` preserves the raw palace
  cells and a separately identified resolved static oracle, independent of the
  production formula. There are **two transcription defects affecting three
  bureau/day cases**, investigated before testing the implementation:

  | Source location | Raw transcription | Adopted resolution | Independent evidence |
  | --- | --- | --- | --- |
  | 木三局 寅 cell | 初三、初九; 初九 is also in 辰, while 初五 is missing | 寅 = 初三、初五; 初九 remains 辰 | CUST PDF p.4 explicitly gives day 5 寅 and day 9 辰; iztro kernel and stated padding rule agree |
  | 金四局 亥 cell | Only 初一; 三十 is missing from the chart | 亥 = 初一、三十 | CUST PDF p.4 explicitly gives day 30 亥; iztro kernel and stated padding rule agree |

- The independent published table used for these resolutions is 翁彩瓊老師講授,
  [室內風水與環境評析：紫微斗數命盤步驟十三至十九](https://cc.cust.edu.tw/~wtcbee/index.files/teaching/98-2/Geomancy2/lesson/18.pdf),
  printed/PDF p.4, **起紫微帝曜檢索表**. The complete relevant page was rendered
  with Poppler and visually checked, not accepted solely from OCR/search text.
  SHA-256: `620744696eea870dca9008605af4b6a01c5aee02248e170e6671413cc7312e86`.
  The resulting 150-case oracle is explicitly **source-transcribed with audited
  corrections**, not a claim that the uncorrected Wikisource chart is complete.
- Secondary engineering reference: [iztro rule documentation](https://iztro.com/learn/setup),
  sections 8-11, plus the actual
  [getStartIndex source](https://github.com/SylarLong/iztro/blob/2c7ef9be669df7b19d1799f4dce335fed3794f78/src/star/location.ts)
  and [getMajorStar source](https://github.com/SylarLong/iztro/blob/2c7ef9be669df7b19d1799f4dce335fed3794f78/src/star/majorStar.ts),
  pinned at commit `2c7ef9be669df7b19d1799f4dce335fed3794f78`.
  Its examples give 木3/day27 -> 戌, 火6/day13 -> 亥, 土5/day6 -> 未.
  The fire example's source comment prints `18 / 8 = 3`; this is an arithmetic
  typo: the specified fire bureau is 6, and executable code divides by 6.
  The expected padding/quotient are respectively **0/9, 5/3, 4/2**; tests check
  both intermediates and branches without adapting expected results to code.

### Phase 1E secondary execution and convention boundaries

`tests/verify_iztro_main_stars.cjs` is an optional development audit, not part of
Python production or pytest. With Node 24 it reads the two downloaded source
files in `tmp/phase1e-iztro`, checks their pinned SHA-256 hashes, strips only
TypeScript/export syntax and executes their actual placement function bodies.
Calendar/bureau inputs are explicitly injected; translation and unused
brightness/transformation services are stubbed. The harness compares full
fourteen-star results with both the independent fixtures and Python outputs.
It installs no iztro package and adds no runtime dependency or network requirement.

Executed result: **150 full-layout MATCH, 0 MISMATCH**, including the three
published examples and all twelve group rotations. This is a **placement-kernel
cross-check**, not a complete external-calendar or proprietary-calculator check.

iztro's source advances a late-Zi day when `timeIndex == 12` and `dayDivide` is
not `current`. The audit explicitly selects `dayDivide: 'current'` and checks
day 30 / 木3 at late-Zi -> 亥. Its other setting is **DIFFERENT_CONVENTION**;
Tiger-ZiWei does not adopt it. External year/leap handling is not compared in
this isolated audit because it injects verified upstream values. An optional
external proprietary full-chart comparison remains **INCONCLUSIVE** (not run
in Phase 1E; Phase 1C already documented NCC's login/subscription restriction).
No access controls were bypassed.

### Phase 1E validation checkpoint

The five classical day-1 anchors are 火6酉、土5午、金4亥、木3辰、水2丑.
All **150** resolved birthday-table entries are tested along with fourteen-star
set completeness and fixed, hand-specified full layouts for every 紫微 position.
The mandatory 木3/day27 and 2025-01-29 00:30 fourteen-star dictionaries are
separate explicit fixtures, not generated by the functions being tested.

| Gregorian input | Lunar day | Bureau | 紫微 | 天府 |
| --- | --- | --- | --- | --- |
| 2025-01-29 00:30 | 1 | 土五局 | 午 | 戌 |
| 2025-01-29 01:30 | 1 | 火六局 | 酉 | 未 |
| 2024-02-29 12:00 | 20 | 金四局 | 午 | 戌 |
| 2025-07-25 12:00 (leap June) | 1 | 土五局 | 午 | 戌 |
| 2025-07-25 14:30 (leap June) | 1 | 火六局 | 酉 | 未 |
| 2025-07-24 23:59 | 30 | 木三局 | 亥 | 巳 |
| 2025-07-25 00:00 (leap June) | 1 | 水二局 | 丑 | 卯 |

These use synthetic female/Taipei BirthData and supplied civil time. Full
fourteen-star layouts, not just the two leaders, are checked in every case.
The same leap date with different hours produces different upstream bureaus;
Phase 1E consumes those results without adding a leap-month rule.

Phase 1E verification on 2026-10-05: the complete suite returned **530 passed,
0 failed** under both `.\.venv311\Scripts\python.exe -m pytest -q` (Python
**3.11.3**) and `python -m pytest -q` (Python **3.14.7**). This includes all
279 Phase 1A-1D tests and 251 new Phase 1E tests. The Python 3.11 run retains
one upstream Starlette/httpx deprecation warning. The optional Node source
audit also passed; Node reports an experimental type-stripping API warning.
Five day-1 anchors, all 150 audited table cases, all twelve 天府 positions,
both groups at all twelve rotations, seven full BirthData cases and the
late-Zi immutability regression passed. No unresolved critical discrepancy.
Phase 1E status: **PASS**, limited to this major-star placement scope.

Brightness / 廟旺利陷, auxiliary/minor stars, 四化, 命主/身主, 長生十二神,
大限/小限/流年, interpretations, PNG, NVIDIA API/LLM and DOCX remain
**NOT IMPLEMENTED**. Passing Phase 1E does not establish complete chart
correctness. Phase 1E itself did not include Phase 1F composition or Phase 2.

## Phase 1F basic-chart composition and manual gate

`calculate_basic_chart(BirthData)` composes the existing Phase 1B calendar,
Phase 1C palaces, Phase 1D bureau and Phase 1E major-star calculations. It adds
no astrology formula. `BasicChartResult` preserves those four upstream receipts,
a frozen birth-input snapshot, and twelve branch-ordered `BasicChartPalace`
records with palace name, Ganzhi, Life/Body markers and grouped major stars.
Calendar and Life/Body convenience properties refer to the upstream objects;
there is no competing calendar or year-boundary path.

Construction and deserialization check twelve unique canonical names/branches,
one Life/Body marker, all stem rotations, Life Ganzhi, bureau, and exactly fourteen
distinct stars grouped under their correct branches. Validation intentionally
reruns the **existing** B-E functions to reject coherent-looking but forged
upstream values. It duplicates no formulas. `model_dump_json(round_trip=True)`
round-trips the complete chart; repeated calculations are identical. Male and
female inputs produce identical current astrology fields; this says nothing
about future gender-dependent luck calculations.

### Full independent-engine comparison

The full [pinned iztro source](https://github.com/SylarLong/iztro/tree/2c7ef9be669df7b19d1799f4dce335fed3794f78)
is compiled only in ignored `tmp/phase1f-iztro`. Unlike Phase 1E's isolated kernel
audit, **no calendar, bureau or other dependencies are stubbed**. Its exact
configuration is `algorithm='default', yearDivide='normal', dayDivide='current'`,
with `fixLeap=true`, `language='zh-TW'`. All compared fields come from the full
`astro.bySolar` result. Names such as 僕役 normalize to 交友宮; canonical output
order is 子 through 亥. Extra auxiliary stars, brightness, transformations and
luck fields are excluded, not implemented in Tiger-ZiWei.

Comparison scope: lunar date, primary year Ganzhi, Life/Body and Body host,
all twelve palace names/stems/Ganzhi, bureau, and all fourteen major stars with
palace grouping. **External month/day/hour Ganzhi are outside this comparison**;
Tiger preserves and tests all four Phase 1B Ganzhi internally. For example,
iztro's normal month setting returns 戊寅 on 2025-01-29 while Tiger's adopted
solar-term-date month is 丁丑. This is not hidden in a claim of all-four-pillars
external equality. No external unsupported fields are used to fail the gate.

Results: five required non-leap cases (2025-01-29 00:30 and 01:30,
2024-02-29 12:00, 2025-01-28 00:30, 2024-02-09 00:30) plus
**2025-07-24 23:59** are **FULL MATCH** within that normalized scope.
The late-Zi date is regular sixth month day 30, not a leap month; selecting
`dayDivide='current'` preserves day 30 and yields Life/Body 未, 木三局, 紫微亥.

The two 2025-07-25 leap-sixth-month cases are **DIFFERENT_CONVENTION**, not
implementation failures. Lunar date and primary year match; first divergence
is Phase 1C Life/Body placement. Tiger uses the next month for the **whole** leap
month, while pinned iztro's `fixLeap=true` advances only after day 15.

| Time | Tiger Life/Body; bureau; 紫微 | iztro Life/Body; bureau; 紫微 |
| --- | --- | --- |
| 12:00 | 寅/寅; 土五局; 午 | 丑/丑; 火六局; 酉 |
| 14:30 | 丑/卯; 火六局; 酉 | 子/寅; 火六局; 酉 |

The second case shares its bureau/star branches but still differs in palace
names/Body location; that is not a full-chart match. No convention was changed.

### Reproduce the development gate

Python and application startup never require Node. External pytest cases run
when Node and the separate built checkout are available; otherwise eight tests
explicitly skip and **the external gate has not been rerun**. Core tests are
offline. To prepare the external engine from the repository root:

```powershell
New-Item -ItemType Directory -Force tmp/phase1f-iztro | Out-Null
Invoke-WebRequest 'https://codeload.github.com/SylarLong/iztro/zip/2c7ef9be669df7b19d1799f4dce335fed3794f78' -OutFile tmp/phase1f-iztro/source.zip
# Extract once into a new/empty destination; do not overwrite an existing checkout.
Expand-Archive tmp/phase1f-iztro/source.zip tmp/phase1f-iztro/source
node tests/setup_iztro_basic_chart.cjs
node tests/verify_iztro_basic_chart.cjs --save-report
.\.venv311\Scripts\python.exe -X utf8 -m scripts.validate_basic_chart --manual-package --save-report
.\.venv311\Scripts\python.exe -m pytest -q
python -m pytest -q
```

The setup checks source archive SHA-256
`794938fbc17331b3cbf66040c39ceb1a82aa21ad31cf7f35f3324e685379da68`, installs
integrity-checked **yarn.lock versions** without lifecycle scripts, and compiles
with TypeScript 5.2.2. Dependencies are dayjs 1.11.10, i18next 23.5.1,
lunar-lite 0.2.8, root lunar-typescript 1.7.8 and its nested 1.8.6,
@babel/runtime 7.26.10 and regenerator-runtime 0.14.0. Build metadata/source hashes
remain in the ignored checkout; no Python requirement or project npm dependency
was added. The verification script emits normalized JSON and stops at the first
unexpected exact-convention discrepancy.

Generated review files: `output/phase1f/iztro-comparison.json` contains both
normalized engines and earliest-divergence classifications;
`output/phase1f/manual-validation.txt` shows three complete non-leap charts and
one separately labelled leap chart palace by palace. They are generated evidence,
not the expected test oracle. The three hand-reviewed static expected charts are
in `tests/basic_chart_reference.py`, independently specified before comparison.

**Phase 1F: INCONCLUSIVE — AUTOMATED GATE PASS, USER MANUAL VALIDATION REQUIRED.**
Execution receipt (2026-10-05): Python **3.11.3** and **3.14.7** each completed
the entire suite with **582 passed, 0 failed, 0 skipped** (all existing 530
regressions plus 52 Phase 1F tests). The eight actual pinned-engine comparison
tests ran in both suites, not merely against saved output. Python 3.11 retained
one existing upstream Starlette/httpx deprecation warning. No critical unresolved
mismatch was found; leap convention differences remain explicitly classified.

The user must inspect 2025-01-29 00:30, 2025-01-29 01:30, 2024-02-29 12:00 and
the separately labelled 2025-07-25 12:00 leap case (all female/Taipei), checking
lunar date, Life/Body, twelve names/stems, bureau and every major star. No user
manual review is recorded yet. **Do not start Phase 2 until manual acceptance
and explicit Phase 1F PASS.**

This remains only the basic core: no auxiliary/minor stars, 四化, 廟旺利陷,
命主/身主, 長生十二神, 大限/小限/流年, interpretation, PNG, NVIDIA API/LLM or
DOCX. The LLM remains completely absent from chart calculation.

## Requirements

- Python 3.11+
- Dependencies listed in `requirements.txt`

## Run

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app
```

The health endpoint is available at `GET /health`.

## Test

```powershell
python -m pytest
```

The existing Python 3.11.3 installation was also used through a project-local
virtual environment:

```powershell
.\.venv311\Scripts\python.exe -m pytest
```

Phase 1B verification on 2026-10-05: `python -m pytest -q` (Python 3.14.7) and
`.\.venv311\Scripts\python.exe -m pytest -q` (Python 3.11.3) each passed all
96 tests, including the 17 Phase 1A tests. No critical reference mismatches.
The 3.11 environment emitted one upstream Starlette warning about its httpx
test-client integration; it did not affect the results.

## Usage

```python
from app.calendar.ganzhi import calculate_calendar
from app.models.birth import BirthData

result = calculate_calendar(BirthData(
    gender="female", birth_year=2025, birth_month=7, birth_day=25,
    birth_hour=14, birth_minute=30, birthplace="Taipei",
))
assert result.lunar_date.is_leap_month
assert result.lunar_date.month == 6

from app.ziwei import calculate_palaces

layout = calculate_palaces(result)
assert layout.effective_lunar_month == 7
assert layout.life_palace_branch == "丑"
assert layout.body_palace_branch == "卯"
assert layout.body_palace_name == "福德宮"

from app.ziwei import calculate_five_elements_bureau

bureau = calculate_five_elements_bureau(result, layout)
assert bureau.year_heavenly_stem == "乙"
assert bureau.life_palace_ganzhi.display == "己丑"
assert bureau.nayin_element == "火"
assert bureau.bureau_name == "火六局"
assert bureau.bureau_number == 6

from app.ziwei import calculate_major_stars

major_stars = calculate_major_stars(result.lunar_date, bureau)
assert major_stars.lunar_day == 1
assert major_stars.ziwei_branch == "酉"
assert major_stars.tianfu_branch == "未"
assert len(major_stars.stars) == 14
```

`NVIDIA_API_KEY` remains optional. `.env.example` documents the placeholder;
`get_settings()` reads the process environment, not an automatically loaded file.

## Phase 2A / 2A-R — Fourteen Auxiliary Stars (closure audit: 2026-10-06)

Status: **INCONCLUSIVE — AUTOMATED GATE PASS, USER MANUAL VALIDATION REQUIRED**.
Phase 2A-R closes the month-star convention blocker through the user's explicit
adoption, not a newly discovered sentence in the classical text. The user manual
gate is **REQUIRED**, not completed. Do not start Phase 2B.
The Phase 2A-R request authorizes this narrow repair; it is not recorded as
retrospective completion of Phase 1F's still-pending manual acceptance.

### Sources and textual decisions

Primary: [《紫微斗數全書》卷二, fixed revision 1963110](https://zh.wikisource.org/w/index.php?title=紫微斗數全書/卷二&oldid=1963110),
specifically 安身命例, 安左輔右弼星訣, 安文昌文曲星訣, 安天魁天鉞訣,
安祿存星訣, 安擎羊陀羅二星訣, 安天馬星訣, 安火鈴二星訣 and 天空地劫訣.
Read the prose examples as well as the verses; transcription is not infallible.

Independent references:

- [晉賢, 安星規律：天魁天鉞的機遇 (2021-12-03)](https://little-yin.com/2021/12/03/opportunity/)
  explicitly specifies the order of 魁 then 鉞 and all five stem groups.
- [《紫微斗數精成》第02章, 第一節 3、6 and 第二節 9](https://www.chinazwds.com/Home/ArticleDetails/7ede7be574fd4990948bb5c0fcc7a0f1)
  discusses numeric lunar months for month-stars and a next-month rule for
  natal charts generally. This supports a next-month interpretation, but does
  not establish what the primary text intended for every month-based star.
  It is a reference-text transcription, not an inspected original book scan.
- [NCC software settings](https://fate.ncc.com.tw/trial/setting) exposes
  current-month, next-month and mid-month split options, plus separate
  palace and month-star leap toggles. This is evidence of software convention
  choices, not a claim of a successfully generated NCC comparison chart.

Secondary engineering cross-check only:
[iztro setup rules, sections 13–17](https://iztro.com/learn/setup), and
[pinned iztro source](https://github.com/SylarLong/iztro/tree/2c7ef9be669df7b19d1799f4dce335fed3794f78)
(`src/star/location.ts`, `minorStar.ts`, `src/utils/index.ts`). iztro does not
override Tiger's selected convention. The original audit was on 2026-10-05;
the primary text, leap reference and NCC settings were rechecked on 2026-10-06.
No source's claimed predictive accuracy is adopted or tested.

魁鉞 audit: the Wikisource transcription has **丙丁豬狗位**, **六辛逢虎馬**,
and **壬癸免蛇藏**. Read literally, the first two conflict with the requested
亥/酉 and 午/寅 pairs. We explicitly adopt the corroborated **豬雞**, **馬虎**,
and **兔蛇** readings, as specified by the task and independently explained
by 晉賢, and also present in pinned iztro. These are documented editorial
resolutions of textual variants/suspected transcription errors, NOT a claim
that the web transcription literally agrees or that a facsimile was checked.
The ten-stem table below is frozen and individually tested.

| 年干 | 天魁 | 天鉞 | 祿存 | 擎羊 | 陀羅 |
|---|---|---|---|---|---|
| 甲 | 丑 | 未 | 寅 | 卯 | 丑 |
| 乙 | 子 | 申 | 卯 | 辰 | 寅 |
| 丙 | 亥 | 酉 | 巳 | 午 | 辰 |
| 丁 | 亥 | 酉 | 午 | 未 | 巳 |
| 戊 | 丑 | 未 | 巳 | 午 | 辰 |
| 己 | 子 | 申 | 午 | 未 | 巳 |
| 庚 | 丑 | 未 | 申 | 酉 | 未 |
| 辛 | 午 | 寅 | 酉 | 戌 | 申 |
| 壬 | 卯 | 巳 | 亥 | 子 | 戌 |
| 癸 | 卯 | 巳 | 子 | 丑 | 亥 |

### Adopted placement rules

Reuse the project's `子丑寅卯辰巳午未申酉戌亥` order, forward +1,
backward -1, modulo 12. No second production branch coordinate system.

| Family | Rule | Static coverage |
|---|---|---|
| 左輔 / 右弼 | effective natal month 1 starts 辰 / 戌; forward / backward month−1 | all 12 ordinary months; whole-leap-month regression |
| 文昌 / 文曲 | 子 hour 戌 / 辰; backward / forward hour index | all 12 hours |
| 天魁 / 天鉞 | table above, primary birth-year stem | all 10 stems |
| 祿存 / 擎羊 / 陀羅 | table for 祿存 only; 羊=祿+1, 陀=祿−1 | all 10 stems |
| 天馬 | 寅午戌→申; 申子辰→寅; 巳酉丑→亥; 亥卯未→巳 | all 12 year branches |
| 火星 / 鈴星 | respective trine 子-hour bases 丑/卯, 寅/戌, 卯/戌, 酉/戌; both forward by hour | all 144 pairs |
| 地空 / 地劫 | 亥 at 子 hour; backward / forward by hour | all 12 hours |

Primary fire/bell verse supplies the bases; iztro's published worked example
clarifies both forward directions. Required 壬辰年卯時 is 火星巳 / 鈴星丑.
The primary 空劫 section's paired 天空 is normalized to **地空** here. There
is no separate 天空 record or implementation of the modern miscellaneous star.
The prose examples disambiguate 左右 month movement and 羊陀 direction.

Inputs come only from existing `CalendarResult.lunar_date`, primary
`year_ganzhi` (Lunar New Year, not January 1 or 立春), and structured
`hour_ganzhi.earthly_branch`. Late 23:00–23:59 is 子 without changing either
civil/lunar date or primary year. The auxiliary module performs no calendar,
Life/Body, bureau, or major-star recalculation. Existing BasicChart validation
continues to call the authoritative upstream functions for integrity; no
upstream formula or expected Phase 1 fixture has been changed.

### Tiger-ZiWei adopted natal leap-month convention

The primary next-month instruction is inside **安身命例**, explicitly discussing
Life/Body. It establishes the basis for Tiger's selected natal convention,
but does **not** explicitly name 左輔/右弼 in its leap-month sentence. The
later/reference 《紫微斗數精成》 charting instructions apply month selection
to natal month-stars and describe next-month handling for natal charts;
NCC exposes leap handling for both palaces and 月系星. These support treating
this as a deliberate charting convention, not proof of universal agreement.

On 2026-10-06 the user explicitly extended the same natal convention to the
currently implemented birth-month stars. **Tiger-ZiWei intentionally uses one
consistent natal-month selection**:

- Ordinary lunar month N → effective natal month N.
- Whole leap lunar month N → effective natal month N+1, without a day-15 split.
- Currently applies to Life/Body and 左輔/右弼 only. Year/hour stars do not use it.
- Reuse `app.ziwei.palace.effective_lunar_month`; no second leap formula.
- Preserve the actual LunarDate month, leap flag and day, and every Ganzhi.
- Existing supported effective-month range stays 1..12. Synthetic leap month 12
  still raises the existing explicit error; do not invent a month-13 rollover.

Other traditions/software may use current month, next month, or a day-15/16
split. Disagreements caused by these choices are **DIFFERENT_CONVENTION**, not
automatically program bugs. The prior INCONCLUSIVE source-scope investigation
is closed by explicit project adoption, not by falsely expanding the quotation.

For L = 2025-07-25 12:00 (乙巳, 閏六月初一, 午):

- Actual lunar month remains **leap 6**, day 1; effective natal month is **7**
  for both Life/Body and the month-dependent auxiliary stars.
- Static expectation and actual result: **左輔戌 / 右弼辰**.
- The other twelve stars are unchanged: 文昌辰、文曲戌、天魁子、天鉞申、祿存卯、擎羊辰、
  陀羅寅、天馬亥、火星酉、鈴星辰、地空巳、地劫巳.
- Pinned iztro with `fixLeap=true` uses month 6 on leap day 1: 左輔酉 / 右弼巳.
  Its `fixLunarMonthIndex` advances after day 15 (subject to its time-index
  handling). L compares all 14 stars: the twelve year/hour stars MATCH, and
  only 左輔/右弼 are **DIFFERENT_CONVENTION**. It is not a FULL MATCH.
  The comparison checks the exact two expected discrepancies; a mismatch in
  any year/hour star is still FAIL, never hidden by the convention label.

### Models and integration

`AuxiliaryStarPlacement` is immutable, has only name and valid branch.
`AuxiliaryStarChart` requires exactly **14** distinct canonical stars, permits
co-location, and exposes fresh `star_to_branch` / `branch_to_stars` mappings.
Its `PASS` status means complete placement, **not human acceptance**.

The temporary partial model and incomplete leap-result path have been removed.
`calculate_auxiliary_stars(calendar)` always returns `AuxiliaryStarChart` for
supported inputs, including leap births on either side of day 15/16.

`BasicChartResult.auxiliary_star_chart` now has one complete type. Every palace
exposes **major_stars** and **auxiliary_stars** separately. Its validator checks
authoritative auxiliary identity, fourteen unique names, and branch grouping.
Legacy partial payloads, forged placements, moved stars, duplicates and missing
stars are rejected. Basic charts retain twelve palaces, fourteen unchanged
major stars, and unchanged Life/Body/bureau values. Serialization is deterministic;
use `model_dump(round_trip=True)` for revalidation. New fields are additive;
old serialized Phase 1F payloads without auxiliary fields require recalculation
from BirthData, rather than silently asserting that missing data is complete.

### Independent fixtures and manual checks

`tests/auxiliary_star_reference.py` contains hand-written ordinary month/hour
rows, ten stem rows, four fully expanded fire/bell hour sequences, and complete
static A/B/C/L expectations. A/B/C and L's previous twelve positions are unchanged;
only L's independently hand-derived 左輔戌 / 右弼辰 are added.
No expected branch is generated by the functions
under test. The following compact receipt uses the canonical star order:

| Case | Birth input (female / Taipei) | Lunar / year / hour | 14 positions in listed star order |
|---|---|---|---|
| A | 2025-01-29 00:30 | 2025 正月初一 / 乙巳 / 子 | 辰 戌 戌 辰 子 申 卯 辰 寅 亥 卯 戌 亥 亥 |
| B | 2025-01-29 01:30 | 2025 正月初一 / 乙巳 / 丑 | 辰 戌 酉 巳 子 申 卯 辰 寅 亥 辰 亥 戌 子 |
| C | 2024-02-29 12:00 | 2024 正月二十 / 甲辰 / 午 | 辰 戌 辰 戌 丑 未 寅 卯 丑 寅 申 辰 巳 巳 |
| L | 2025-07-25 12:00 | 2025 閏六月初一 / 乙巳 / 午 | 戌 辰 辰 戌 子 申 卯 辰 寅 亥 酉 辰 巳 巳 |

Order: 左輔、右弼、文昌、文曲、天魁、天鉞、祿存、擎羊、陀羅、天馬、
火星、鈴星、地空、地劫. Z = 2025-07-24 23:59 stays 2025 六月三十,
乙巳, 子; 左輔酉、右弼巳 and the same twelve year/hour positions as A.

Run from project root (normal runtime never needs Node):

```powershell
python -m scripts.validate_auxiliary_stars
.\.venv311\Scripts\python.exe -m scripts.validate_auxiliary_stars --save-report
.\.venv311\Scripts\python.exe -m pytest -q
python -m pytest -q
```

The manual package is `output/phase2a/manual-validation.txt` (UTF-8). Inspect
A/B/C/L's input, lunar date, primary year, hour, actual month and leap flag,
effective natal month, all 14 stars, and all twelve palace groupings.
For L explicitly check actual leap month 6, effective month 7, 左輔戌 / 右弼辰.
Check Z's unadvanced date and 子-hour stars. User review is still REQUIRED.

Optional developer comparison, only where Node and the separately prepared
pinned Phase 1F checkout already exist:

```powershell
node tests/verify_iztro_auxiliary_stars.cjs --save-report
```

It verifies the pinned source hashes, runs the full engine and actual pinned
lunar dependencies, and saves `output/phase2a/iztro-comparison.json`. No mocked
placement functions; only the fourteen requested names are projected, ignoring
external 四化/brightness and other fields. A/B/C/Z: 14 of 14 positions match.
L: twelve year/hour positions MATCH; 左輔/右弼 DIFFERENT_CONVENTION. Configuration:
`algorithm=default`, `yearDivide=normal`, `dayDivide=current`, `fixLeap=true`,
`zh-TW`. No Node or iztro production dependency and no runtime installation.
This execution used Codex's **existing bundled** Node, not a user Node install.
Optional external pytest cases explicitly skip if Node or the dev build is
absent; all static and integration tests continue normally.

Phase 2A-R execution receipt (2026-10-06):

| Command / environment | Passed | Failed | Skipped |
|---|---:|---:|---:|
| `.\.venv311\Scripts\python.exe -m pytest -q` (Python 3.11.3) | 849 | 0 | 0 |
| `python -m pytest -q` (Python 3.14.7) | 849 | 0 | 0 |
| Python 3.11.3, PATH restricted inside Python and `shutil.which('node') is None` asserted | 836 | 0 | 13 |

The no-Node run skips only eight Phase 1F and five Phase 2A optional external
comparisons, with explicit missing dev-engine/Node reasons. One existing
Starlette/httpx deprecation warning remains in Python 3.11; no dependencies
were changed to address that unrelated warning. The initial new manual-output
test exposed Windows CRLF handling in the test's text parsing; it was fixed
and both complete suites above were rerun successfully. Phase 1 fixtures and
non-leap Phase 2A expected star positions were not changed.

The generated manual and iztro reports at the paths above have been refreshed
for complete L output. Automated acceptance is PASS; user acceptance remains
REQUIRED.

## Phase 2B — Birth-year Four Transformations (2026-10-06)

Status: **INCONCLUSIVE — AUTOMATED GATE PASS, USER MANUAL VALIDATION REQUIRED**.
This phase only tags four already-positioned natal stars from the primary
birth-year Heavenly Stem. It adds no interpretation and never moves or creates
a star.

### Source resolution and the 壬 edition variant

Primary evidence is the 南陽堂刊本《新鐫希夷陳先生紫微斗數全書》 and its
Wikisource transcription, `安祿權科忌四星變化訣`. The mnemonic explicitly
states the order through the 甲 example as 祿、權、科、忌. The primary line is
`壬梁紫府武`, so its 壬 化科 target is **天府**:

- [Wikisource fixed revision 1963110](https://zh.wikisource.org/w/index.php?title=紫微斗數全書/卷二&oldid=1963110)
- [南陽堂刊本 scan/index copy](https://vr-d.com/pdf-file/紫微斗數/紫微斗數全书.七卷.明代南阳堂刊本.pdf)
- [parallel full-book transcription/PDF, pp. 354–355](https://www.huyenhocvietnam.vn/upload/attach/hhvn2021712151247jof6Iu.pdf)

Two independent older/parallel witnesses instead read `壬梁紫左武`:

- [明萬曆九年《紫微斗數捷覽》, 安祿權科忌四化訣](https://shixingji.club/public/ziweidoushujielan)
- The late-Qing `紫微斗數全集` tradition, summarized side-by-side with `全書`
  in the [edition comparison table](https://zh.wikipedia.org/wiki/紫微斗數#安四化星),
  also uses 左輔. Pinned iztro independently implements this 左輔 row.

This is not treated as a simple Wikisource typo: the primary 南陽堂 witness and
parallel full-book copy agree on 府, while 捷覽/全集 and iztro agree on 左.
Tiger-ZiWei follows its declared primary `全書` edition and therefore adopts
**壬：天梁化祿、紫微化權、天府化科、武曲化忌**. The disagreement is
classified **EDITION_VARIANT**. No claim is made that other schools are wrong.

### Frozen birth-year table

Canonical order is 化祿、化權、化科、化忌:

| 年干 | 化祿 | 化權 | 化科 | 化忌 |
|---|---|---|---|---|
| 甲 | 廉貞 | 破軍 | 武曲 | 太陽 |
| 乙 | 天機 | 天梁 | 紫微 | 太陰 |
| 丙 | 天同 | 天機 | 文昌 | 廉貞 |
| 丁 | 太陰 | 天同 | 天機 | 巨門 |
| 戊 | 貪狼 | 太陰 | 右弼 | 天機 |
| 己 | 武曲 | 貪狼 | 天梁 | 文曲 |
| 庚 | 太陽 | 武曲 | 太陰 | 天同 |
| 辛 | 巨門 | 太陽 | 文曲 | 文昌 |
| 壬 | 天梁 | 紫微 | 天府 | 武曲 |
| 癸 | 破軍 | 巨門 | 太陰 | 貪狼 |

`app.ziwei.transformations` consumes only `CalendarResult.year_ganzhi.heavenly_stem`.
It looks each selected name up exactly once across the existing fourteen major
and fourteen auxiliary stars, copies that star's existing branch, then resolves
the existing palace name from `PalaceLayout`. `BasicChartResult` stores the one
validated four-record result; palaces do not duplicate it. Model validation
requires one record each in canonical 祿權科忌 order and four unique targets.

The independent fixture in `tests/transformation_reference.py` contains forty
literal assignments and full A/B/C/L/Z records. 2025-01-28/29 proves the stem
switch is Lunar New Year, not Li Chun. A/B/C/L/Z verify unchanged branches and
palaces, including two B targets sharing 疾厄宮, L using only its 乙 birth-year
stem, and Z preserving the current civil/lunar day and 子 hour.

Run the manual package from the project root:

```powershell
.\.venv311\Scripts\python.exe -m scripts.validate_transformations
```

It prints the frozen ten-stem table once, followed by A/B/C/L/Z Gregorian and
lunar inputs, primary year Ganzhi/stem, and each target's category, branch and
palace. Optional pinned iztro comparison is development-only and requires no
production Node dependency. Its expected result is 39/40 table assignments
matching, with only 壬化科 classified `EDITION_VARIANT`; full A/B/C/Z locations
match, while L location differences remain the already-documented upstream
leap-month `DIFFERENT_CONVENTION`.

Phase 2B automated receipt:

| Command / environment | Passed | Failed | Skipped |
|---|---:|---:|---:|
| `.\.venv311\Scripts\python.exe -m pytest -q` (Python 3.11.3, bundled Node available) | 890 | 0 | 0 |
| Python 3.11.3 with `PATH` cleared inside the Python process | 871 | 0 | 19 |

The 19 no-Node skips are only the eight Phase 1F, five Phase 2A and six Phase
2B optional pinned-engine comparisons. All production/static/integration tests
pass without Node. The existing Starlette/httpx deprecation warning is unrelated.

Still NOT IMPLEMENTED: palace-stem 四化, major-luck/annual/monthly/daily 四化,
self-transformation, flying transformation, interpretation, brightness,
命主/身主, other miscellaneous stars, 長生十二神, 大限, 小限, 流年, PNG
rendering, NVIDIA API/LLM, and DOCX. Stop at the Phase 2B manual gate.

## Phase 2B-UI — local manual-validation page

The dependency-free browser interface at `/ziwei` sends ordinary birth-form
input to `POST /api/chart` and renders the existing `BasicChartResult`. Python
remains the sole calculation authority; the JavaScript only gathers input and
renders returned values. The page includes A/B/C/L/Z presets, all twelve
palaces, fourteen major stars, fourteen auxiliary stars, and the four
birth-year transformations. It makes no NVIDIA, LLM, or external network call.

Start the local UI with Python 3.11.3 from the project root:

```powershell
.\.venv311\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 18080
```

Then open `http://127.0.0.1:18080/ziwei`. Automated verification does not
complete the human gate: manually inspect A/B/C/L/Z before accepting Phase 2B.

## Phase 3A — formal PNG chart renderer

Phase 3A adds the first formal chart image renderer. The `/ziwei` page now
generates an original, light-background PNG alongside the existing summary and
validation tables. `POST /api/chart/png` accepts the same `BirthData` JSON as
`POST /api/chart`, runs the existing deterministic pipeline, saves the image,
and returns it as `image/png`. The browser shows a preview and a `下載 PNG`
link; no browser screenshot or frontend calculation is involved.

Images are saved under `output/charts/`. A supplied name becomes
`<sanitized-name>_紫微命盤.png`; otherwise the renderer uses
`YYYY-MM-DD_HHMM_紫微命盤.png`. Repeating the same input intentionally replaces
that input's deterministic output, without touching unrelated chart files.

The stable square layout follows this Earthly-Branch map:

```text
巳  午  未  申
辰  [center] 酉
卯  [center] 戌
寅  丑  子  亥
```

Each outer palace shows its name, branch/Ganzhi, Life/Body markers, major stars,
auxiliary stars, and attached birth-year transformations. The center shows the
verified birth/calendar/palace/bureau fields and a compact Four Transformations
summary. On Windows, Microsoft JhengHei is preferred, followed by MingLiU and
KaiU; `TIGER_ZIWEI_FONT` can explicitly select another installed Chinese font.
Missing usable Chinese fonts produce a clear error instead of unreadable text.

The Phase 3A-R visual refinement preserves the same square geometry and data.
Palace names and major stars now lead the hierarchy, auxiliary stars are quieter,
Life/Body use compact `【命】` / `【身】` markers, and transformations appear beside
their affected stars as `【祿】`、`【權】`、`【科】`、`【忌】`. The center is grouped
into 基本資料、曆法、命盤、月規則、生年四化. The browser preview can be
clicked or opened with `放大查看`, while the original PNG download remains.

This remains a placement renderer for manual validation. Interpretation, DOCX,
LLM/NVIDIA integration, brightness, 大限、流年、小限、長生十二神, additional
stars, and the final report generator remain **NOT IMPLEMENTED**. Automated
tests do not complete the Phase 3A visual gate; manually render and inspect
A/B/C/L/Z before continuing.
