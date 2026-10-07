package com.tiger.ziwei.core

import com.google.gson.Gson
import com.google.gson.GsonBuilder
import java.time.LocalDate

val HEAVENLY_STEMS = listOf("甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸")
val EARTHLY_BRANCHES = listOf("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥")
val PALACE_ORDER = listOf("命宮", "兄弟宮", "夫妻宮", "子女宮", "財帛宮", "疾厄宮", "遷移宮", "交友宮", "官祿宮", "田宅宮", "福德宮", "父母宮")
val FLOW_PALACE_ORDER = listOf("命宮", "父母宮", "福德宮", "田宅宮", "官祿宮", "交友宮", "遷移宮", "疾厄宮", "財帛宮", "子女宮", "夫妻宮", "兄弟宮")
val TRANSFORMATION_ORDER = listOf("化祿", "化權", "化科", "化忌")
val BUREAU_START_AGES = mapOf("水二局" to 2, "木三局" to 3, "金四局" to 4, "土五局" to 5, "火六局" to 6)

val TRANSFORMATION_TARGETS_BY_STEM = linkedMapOf(
    "甲" to listOf("廉貞", "破軍", "武曲", "太陽"),
    "乙" to listOf("天機", "天梁", "紫微", "太陰"),
    "丙" to listOf("天同", "天機", "文昌", "廉貞"),
    "丁" to listOf("太陰", "天同", "天機", "巨門"),
    "戊" to listOf("貪狼", "太陰", "右弼", "天機"),
    "己" to listOf("武曲", "貪狼", "天梁", "文曲"),
    "庚" to listOf("太陽", "武曲", "太陰", "天同"),
    "辛" to listOf("巨門", "太陽", "文曲", "文昌"),
    "壬" to listOf("天梁", "紫微", "天府", "武曲"),
    "癸" to listOf("破軍", "巨門", "太陰", "貪狼"),
)

object ZiweiCore {
    val gson: Gson = GsonBuilder().serializeNulls().disableHtmlEscaping().create()

    private val fiveTigerStarts = mapOf(
        "甲" to "丙", "己" to "丙", "乙" to "戊", "庚" to "戊",
        "丙" to "庚", "辛" to "庚", "丁" to "壬", "壬" to "壬",
        "戊" to "甲", "癸" to "甲",
    )
    private val majorNames = setOf(
        "紫微", "天機", "太陽", "武曲", "天同", "廉貞", "天府",
        "太陰", "貪狼", "巨門", "天相", "天梁", "七殺", "破軍",
    )
    private val nayin = buildNayin()

    fun calculateChart(input: BirthInput): BasicChartResult {
        val birth = TigerCalendar.normalizeBirth(input)
        val calendar = TigerCalendar.calendar(birth)
        val layout = palaceLayout(calendar)
        val stems = palaceStems(calendar.year_ganzhi.heavenly_stem)
        val lifeGanzhi = GanzhiResult(stems.getValue(layout.life_palace_branch), layout.life_palace_branch)
        val element = nayin.getValue(lifeGanzhi.display)
        val bureauName = mapOf("水" to "水二局", "木" to "木三局", "金" to "金四局", "土" to "土五局", "火" to "火六局").getValue(element)
        val bureauNumber = BUREAU_START_AGES.getValue(bureauName)
        val bureau = BureauResult(
            calendar.year_ganzhi.heavenly_stem,
            stems.getValue("寅"),
            lifeGanzhi,
            element,
            lifeGanzhi.heavenly_stem,
            lifeGanzhi.earthly_branch,
            bureauName,
            bureauNumber,
        )
        val majorStars = majorStars(calendar.lunar_date.day, bureauNumber)
        val auxiliaryStars = auxiliaryStars(calendar, layout.effective_lunar_month)
        val positions = layout.palaces.associateBy { it.earthly_branch }
        val palaces = EARTHLY_BRANCHES.map { branch ->
            val position = positions.getValue(branch)
            val ganzhi = GanzhiResult(stems.getValue(branch), branch)
            Palace(
                position.name, ganzhi, position.has_body_palace,
                majorStars.filter { it.earthly_branch == branch },
                auxiliaryStars.filter { it.earthly_branch == branch },
                branch, ganzhi.heavenly_stem, position.is_life_palace,
            )
        }
        val birthTransformations = birthTransformations(calendar.year_ganzhi.heavenly_stem, palaces)
        val majorLuck = majorLuck(calendar.year_ganzhi.heavenly_stem, birth.gender, bureau, palaces)
        val ziwei = majorStars.first { it.name == "紫微" }.earthly_branch
        val tianfu = majorStars.first { it.name == "天府" }.earthly_branch
        return BasicChartResult(
            birth, calendar, layout, bureau,
            MajorStarChart(calendar.lunar_date.day, element, majorStars, bureauName, bureauNumber, ziwei, tianfu),
            AuxiliaryStarChart(stars = auxiliaryStars), birthTransformations, palaces, majorLuck,
            layout.life_palace_branch, layout.body_palace_branch, layout.body_palace_name,
        )
    }

    fun chartJson(inputJson: String): String = gson.toJson(calculateChart(gson.fromJson(inputJson, BirthInput::class.java)))

    fun calculateFlowQuery(chart: BasicChartResult, input: FlowQueryInput): FlowQueryResult {
        require(input.mode == "solar" || input.mode == "lunar")
        require(input.year in 1583..9999)
        require(input.month == null || input.month in 1..12)
        require(input.day == null || input.day in 1..31)
        require(!input.is_leap_month || input.month != null)
        val normalized: NormalizedFlowTarget
        val original: Any
        var completeSolar: LocalDate? = null
        if (input.mode == "solar") {
            val month = requireNotNull(input.month)
            val day = requireNotNull(input.day)
            completeSolar = LocalDate.of(input.year, month, day)
            val lunar = TigerCalendar.toLunar(completeSolar)
            normalized = NormalizedFlowTarget(
                input_mode = "solar", original_solar_date = completeSolar.toString(),
                original_is_leap_month = null, lunar_year = lunar.year, lunar_month = lunar.month,
                lunar_day = lunar.day, is_leap_month = lunar.is_leap_month,
                effective_month = effectiveMonth(lunar.month, lunar.is_leap_month),
            )
            original = SolarFlowQuery(year = input.year, month = month, day = day)
        } else {
            require(input.day == null || input.month != null)
            if (input.month != null) {
                val testDate = LunarDateResult(input.year, input.month, input.day ?: 1, input.is_leap_month)
                val solar = TigerCalendar.toSolar(testDate)
                if (input.day != null) completeSolar = solar
            }
            normalized = NormalizedFlowTarget(
                input_mode = "lunar", original_lunar_year = input.year,
                original_lunar_month = input.month, original_lunar_day = input.day,
                original_is_leap_month = input.is_leap_month,
                converted_solar_date = completeSolar?.toString(), lunar_year = input.year,
                lunar_month = input.month, lunar_day = input.day, is_leap_month = input.is_leap_month,
                effective_month = input.month?.let { effectiveMonth(it, input.is_leap_month) },
            )
            original = LunarFlowQuery(year = input.year, month = input.month, day = input.day, is_leap_month = input.is_leap_month)
        }
        if (completeSolar != null) {
            val birthDate = LocalDate.of(chart.birth_data.birth_year, chart.birth_data.birth_month, chart.birth_data.birth_day)
            require(!completeSolar.isBefore(birthDate))
        }
        val year = flowYear(chart, normalized.lunar_year)
        var month: FlowMonthResult? = null
        var day: FlowDayResult? = null
        if (normalized.lunar_month != null) {
            val calendar = completeSolar?.let { TigerCalendar.calendar(it, 0, 0) }
            val monthGanzhi = calendar?.month_ganzhi
                ?: TigerCalendar.lunarMonthGanzhi(normalized.lunar_year, normalized.lunar_month)
            month = flowMonth(
                chart, year, normalized.lunar_year, normalized.lunar_month,
                normalized.is_leap_month, monthGanzhi,
            )
            if (normalized.lunar_day != null) {
                require(calendar != null)
                day = flowDay(
                    chart, month, normalized.lunar_year, normalized.lunar_month,
                    normalized.lunar_day, normalized.is_leap_month, calendar.day_ganzhi,
                )
            }
        }
        return FlowQueryResult(input.mode, original, normalized, year, month, day)
    }

    fun flowQueryJson(chartJson: String, queryJson: String): String {
        val chart = gson.fromJson(chartJson, BasicChartResult::class.java)
        val query = gson.fromJson(queryJson, FlowQueryInput::class.java)
        return gson.toJson(calculateFlowQuery(chart, query))
    }

    fun flowYear(chart: BasicChartResult, targetYear: Int): FlowYearResult {
        require(targetYear in 1583..9999)
        val ganzhi = TigerCalendar.lunarYearGanzhi(targetYear)
        val nominalAge = targetYear - chart.calendar.lunar_date.year + 1
        require(nominalAge >= 1)
        val active = chart.major_luck.periods.find { nominalAge in it.start_nominal_age..it.end_nominal_age }
        val hosts = chart.palaces.associateBy { it.earthly_branch }
        val branches = rotateForward(ganzhi.earthly_branch)
        val palaces = FLOW_PALACE_ORDER.zip(branches).map { (name, branch) ->
            val host = hosts.getValue(branch)
            FlowYearPalace(name, branch, host.palace_name, host.heavenly_stem, host.palace_ganzhi)
        }
        return FlowYearResult(
            targetYear, ganzhi.heavenly_stem, ganzhi.earthly_branch, ganzhi, nominalAge,
            ganzhi.earthly_branch, palaces,
            locatedTransformations(ganzhi.heavenly_stem, chart.palaces), active,
            nominalAge < chart.major_luck.periods.first().start_nominal_age,
            nominalAge > chart.major_luck.periods.last().end_nominal_age,
        )
    }

    private fun flowMonth(
        chart: BasicChartResult,
        flowYear: FlowYearResult,
        lunarYear: Int,
        lunarMonth: Int,
        leap: Boolean,
        monthGanzhi: GanzhiResult,
    ): FlowMonthResult {
        val effective = effectiveMonth(lunarMonth, leap)
        val lifeIndex = (
            EARTHLY_BRANCHES.indexOf(flowYear.flow_life_palace_branch)
                + EARTHLY_BRANCHES.indexOf(chart.calendar.hour_ganzhi.earthly_branch)
                + effective - chart.palace_layout.effective_lunar_month
            ).floorMod(12)
        val lifeBranch = EARTHLY_BRANCHES[lifeIndex]
        val hosts = chart.palaces.associateBy { it.earthly_branch }
        val palaces = FLOW_PALACE_ORDER.zip(rotateForward(lifeBranch)).map { (name, branch) ->
            val host = hosts.getValue(branch)
            FlowPeriodPalace(name, branch, host.palace_name, host.palace_ganzhi)
        }
        val host = hosts.getValue(lifeBranch)
        return FlowMonthResult(
            lunarYear, lunarMonth, leap, effective, monthGanzhi, lifeBranch,
            host.palace_name, host.palace_ganzhi, palaces,
            flowPeriodTransformations(monthGanzhi.heavenly_stem, chart.palaces),
        )
    }

    private fun flowDay(
        chart: BasicChartResult,
        month: FlowMonthResult,
        lunarYear: Int,
        lunarMonth: Int,
        lunarDay: Int,
        leap: Boolean,
        dayGanzhi: GanzhiResult,
    ): FlowDayResult {
        val lifeIndex = (EARTHLY_BRANCHES.indexOf(month.flow_month_life_palace_branch) + lunarDay - 1).floorMod(12)
        val lifeBranch = EARTHLY_BRANCHES[lifeIndex]
        val hosts = chart.palaces.associateBy { it.earthly_branch }
        val palaces = FLOW_PALACE_ORDER.zip(rotateForward(lifeBranch)).map { (name, branch) ->
            val host = hosts.getValue(branch)
            FlowPeriodPalace(name, branch, host.palace_name, host.palace_ganzhi)
        }
        val host = hosts.getValue(lifeBranch)
        return FlowDayResult(
            lunarYear, lunarMonth, lunarDay, leap, dayGanzhi, lifeBranch,
            host.palace_name, host.palace_ganzhi, palaces,
            flowPeriodTransformations(dayGanzhi.heavenly_stem, chart.palaces),
        )
    }

    private fun palaceLayout(calendar: CalendarResult): PalaceLayout {
        val effective = effectiveMonth(calendar.lunar_date.month, calendar.lunar_date.is_leap_month)
        require(effective <= 12)
        val hourIndex = EARTHLY_BRANCHES.indexOf(calendar.hour_ganzhi.earthly_branch)
        val monthStart = (EARTHLY_BRANCHES.indexOf("寅") + effective - 1).floorMod(12)
        val lifeIndex = (monthStart - hourIndex).floorMod(12)
        val bodyIndex = (monthStart + hourIndex).floorMod(12)
        val palaces = PALACE_ORDER.mapIndexed { offset, name ->
            val branchIndex = (lifeIndex - offset).floorMod(12)
            PalacePosition(name, EARTHLY_BRANCHES[branchIndex], branchIndex == bodyIndex, offset == 0)
        }
        val body = palaces.first { it.has_body_palace }
        return PalaceLayout(effective, calendar.hour_ganzhi.earthly_branch, palaces,
            palaces.first().earthly_branch, body.earthly_branch, body.name)
    }

    private fun palaceStems(yearStem: String): Map<String, String> {
        val start = HEAVENLY_STEMS.indexOf(fiveTigerStarts.getValue(yearStem))
        val yin = EARTHLY_BRANCHES.indexOf("寅")
        return (0 until 12).associate { offset ->
            EARTHLY_BRANCHES[(yin + offset) % 12] to HEAVENLY_STEMS[(start + offset) % 10]
        }
    }

    private fun majorStars(lunarDay: Int, bureauNumber: Int): List<StarPlacement> {
        val offset = (-lunarDay).floorMod(bureauNumber)
        val quotient = (lunarDay + offset) / bureauNumber
        val base = (EARTHLY_BRANCHES.indexOf("寅") + quotient - 1).floorMod(12)
        val ziweiIndex = (base + if (offset % 2 == 0) offset else -offset).floorMod(12)
        val tianfuIndex = (2 * EARTHLY_BRANCHES.indexOf("寅") - ziweiIndex).floorMod(12)
        val ziweiGroup = listOf("紫微" to 0, "天機" to -1, "太陽" to -3, "武曲" to -4, "天同" to -5, "廉貞" to -8)
        val tianfuGroup = listOf("天府" to 0, "太陰" to 1, "貪狼" to 2, "巨門" to 3, "天相" to 4, "天梁" to 5, "七殺" to 6, "破軍" to 10)
        return ziweiGroup.map { StarPlacement(it.first, EARTHLY_BRANCHES[(ziweiIndex + it.second).floorMod(12)]) } +
            tianfuGroup.map { StarPlacement(it.first, EARTHLY_BRANCHES[(tianfuIndex + it.second).floorMod(12)]) }
    }

    private fun auxiliaryStars(calendar: CalendarResult, effectiveMonth: Int): List<StarPlacement> {
        fun move(branch: String, offset: Int) = EARTHLY_BRANCHES[(EARTHLY_BRANCHES.indexOf(branch) + offset).floorMod(12)]
        val stem = calendar.year_ganzhi.heavenly_stem
        val branch = calendar.year_ganzhi.earthly_branch
        val hour = calendar.hour_ganzhi.earthly_branch
        val hourIndex = EARTHLY_BRANCHES.indexOf(hour)
        val kuiYue = mapOf(
            "甲" to ("丑" to "未"), "乙" to ("子" to "申"), "丙" to ("亥" to "酉"),
            "丁" to ("亥" to "酉"), "戊" to ("丑" to "未"), "己" to ("子" to "申"),
            "庚" to ("丑" to "未"), "辛" to ("午" to "寅"), "壬" to ("卯" to "巳"), "癸" to ("卯" to "巳"),
        ).getValue(stem)
        val lu = mapOf("甲" to "寅", "乙" to "卯", "丙" to "巳", "丁" to "午", "戊" to "巳", "己" to "午", "庚" to "申", "辛" to "酉", "壬" to "亥", "癸" to "子").getValue(stem)
        val group = when {
            branch in "寅午戌" -> listOf("申", "丑", "卯")
            branch in "申子辰" -> listOf("寅", "寅", "戌")
            branch in "巳酉丑" -> listOf("亥", "卯", "戌")
            else -> listOf("巳", "酉", "戌")
        }
        return listOf(
            StarPlacement("左輔", move("辰", effectiveMonth - 1)),
            StarPlacement("右弼", move("戌", 1 - effectiveMonth)),
            StarPlacement("文昌", move("戌", -hourIndex)),
            StarPlacement("文曲", move("辰", hourIndex)),
            StarPlacement("天魁", kuiYue.first), StarPlacement("天鉞", kuiYue.second),
            StarPlacement("祿存", lu), StarPlacement("擎羊", move(lu, 1)), StarPlacement("陀羅", move(lu, -1)),
            StarPlacement("天馬", group[0]), StarPlacement("火星", move(group[1], hourIndex)),
            StarPlacement("鈴星", move(group[2], hourIndex)), StarPlacement("地空", move("亥", -hourIndex)),
            StarPlacement("地劫", move("亥", hourIndex)),
        )
    }

    private fun birthTransformations(stem: String, palaces: List<Palace>): BirthYearTransformations {
        val stars = allStars(palaces)
        val transformations = TRANSFORMATION_ORDER.zip(TRANSFORMATION_TARGETS_BY_STEM.getValue(stem)).map { (type, target) ->
            val star = stars.getValue(target)
            val palace = palaces.first { it.earthly_branch == star.earthly_branch }
            Transformation(type, target, star.earthly_branch, palace.palace_name, category(target))
        }
        return BirthYearTransformations(stem, transformations)
    }

    private fun majorLuck(stem: String, gender: String, bureau: BureauResult, palaces: List<Palace>): MajorLuckResult {
        val yang = stem in setOf("甲", "丙", "戊", "庚", "壬")
        val forward = (yang && gender == "male") || (!yang && gender == "female")
        val direction = if (forward) "順行" else "逆行"
        val hosts = palaces.associateBy { it.earthly_branch }
        val lifeIndex = EARTHLY_BRANCHES.indexOf(palaces.first { it.is_life_palace }.earthly_branch)
        val periods = (1..12).map { index ->
            val branch = EARTHLY_BRANCHES[(lifeIndex + (if (forward) 1 else -1) * (index - 1)).floorMod(12)]
            val host = hosts.getValue(branch)
            val start = bureau.bureau_number + 10 * (index - 1)
            MajorLuckPeriod(index, start, start + 9, branch, host.palace_name, host.heavenly_stem, host.palace_ganzhi)
        }
        val periodTransformations = periods.map { period ->
            MajorLuckPeriodTransformations(
                period.index, period.start_nominal_age, period.end_nominal_age,
                period.heavenly_stem, period.earthly_branch, period.palace_name,
                locatedTransformations(period.heavenly_stem, palaces),
            )
        }
        return MajorLuckResult(
            bureau.bureau_name, bureau.bureau_number, stem, if (yang) "陽" else "陰",
            gender, direction, periods, periodTransformations,
        )
    }

    private fun locatedTransformations(stem: String, palaces: List<Palace>): List<LocatedTransformation> {
        val stars = allStars(palaces)
        return TRANSFORMATION_ORDER.zip(TRANSFORMATION_TARGETS_BY_STEM.getValue(stem)).map { (type, target) ->
            val star = stars.getValue(target)
            val host = palaces.first { it.earthly_branch == star.earthly_branch }
            LocatedTransformation(type, target, category(target), star.earthly_branch, host.palace_name)
        }
    }

    private fun flowPeriodTransformations(stem: String, palaces: List<Palace>): List<FlowPeriodTransformation> {
        return locatedTransformations(stem, palaces).map {
            FlowPeriodTransformation(it.transformation_type, it.star_name, it.star_category, it.earthly_branch, it.natal_palace_name)
        }
    }

    private fun allStars(palaces: List<Palace>): Map<String, StarPlacement> =
        palaces.flatMap { it.major_stars + it.auxiliary_stars }.associateBy { it.name }

    private fun category(star: String) = if (star in majorNames) "major" else "auxiliary"
    private fun effectiveMonth(month: Int, leap: Boolean) = month + if (leap) 1 else 0
    private fun rotateForward(branch: String): List<String> {
        val start = EARTHLY_BRANCHES.indexOf(branch)
        return (0 until 12).map { EARTHLY_BRANCHES[(start + it) % 12] }
    }

    private fun buildNayin(): Map<String, String> {
        val rows = listOf(
            Triple("甲子", "乙丑", "金"), Triple("丙寅", "丁卯", "火"), Triple("戊辰", "己巳", "木"),
            Triple("庚午", "辛未", "土"), Triple("壬申", "癸酉", "金"), Triple("甲戌", "乙亥", "火"),
            Triple("丙子", "丁丑", "水"), Triple("戊寅", "己卯", "土"), Triple("庚辰", "辛巳", "金"),
            Triple("壬午", "癸未", "木"), Triple("甲申", "乙酉", "水"), Triple("丙戌", "丁亥", "土"),
            Triple("戊子", "己丑", "火"), Triple("庚寅", "辛卯", "木"), Triple("壬辰", "癸巳", "水"),
            Triple("甲午", "乙未", "金"), Triple("丙申", "丁酉", "火"), Triple("戊戌", "己亥", "木"),
            Triple("庚子", "辛丑", "土"), Triple("壬寅", "癸卯", "金"), Triple("甲辰", "乙巳", "火"),
            Triple("丙午", "丁未", "水"), Triple("戊申", "己酉", "土"), Triple("庚戌", "辛亥", "金"),
            Triple("壬子", "癸丑", "木"), Triple("甲寅", "乙卯", "水"), Triple("丙辰", "丁巳", "土"),
            Triple("戊午", "己未", "火"), Triple("庚申", "辛酉", "木"), Triple("壬戌", "癸亥", "水"),
        )
        return buildMap { rows.forEach { (a, b, element) -> put(a, element); put(b, element) } }
    }
}

private fun Int.floorMod(modulus: Int): Int = ((this % modulus) + modulus) % modulus
