package com.tiger.ziwei.core

data class RenderCell(
    val branch: String,
    val palace: String,
    val ganzhi: String,
    val majorStars: List<String>,
    val auxiliaryStars: List<String>,
    val markers: List<String>,
    val majorLuckAge: String,
)

data class ChartRenderStructure(
    val width: Int,
    val height: Int,
    val title: String,
    val centerLines: List<String>,
    val cells: List<RenderCell>,
)

object ChartRenderData {
    const val SIZE = 1648
    fun filename(chart: BasicChartResult): String {
        val b = chart.birth_data
        val base = b.name ?: "%04d-%02d-%02d_%02d%02d".format(java.util.Locale.ROOT, b.birth_year, b.birth_month, b.birth_day, b.birth_hour, b.birth_minute)
        val safe = base.replace(Regex("[^\\p{L}\\p{N}_\\-]+"), "_").trim('_').ifBlank { "Tiger-ZiWei" }
        return "${safe}_紫微命盤.png"
    }
    fun from(chart: BasicChartResult): ChartRenderStructure {
        val transforms = chart.birth_year_transformations.transformations.associateBy { it.star_name }
        val ages = chart.major_luck.periods.associateBy { it.earthly_branch }
        return ChartRenderStructure(
            SIZE, SIZE, "Tiger-ZiWei 紫微斗數命盤",
            listOf(
                chart.birth_data.name?.takeIf { it.isNotBlank() } ?: "未填姓名",
                "國曆 ${chart.calendar.solar_date} ${chart.calendar.solar_time}",
                "農曆 ${chart.calendar.lunar_date.year} 年 ${if (chart.calendar.lunar_date.is_leap_month) "閏" else ""}${chart.calendar.lunar_date.month} 月 ${chart.calendar.lunar_date.day} 日",
                "四柱 ${chart.calendar.year_ganzhi.display} ${chart.calendar.month_ganzhi.display} ${chart.calendar.day_ganzhi.display} ${chart.calendar.hour_ganzhi.display}",
                "${chart.five_elements_bureau.bureau_name}　命宮 ${chart.life_palace_branch}　身宮 ${chart.body_palace_branch}",
            ),
            chart.palaces.map { p ->
                val stars = p.major_stars + p.auxiliary_stars
                RenderCell(
                    p.earthly_branch, p.palace_name, p.palace_ganzhi.display,
                    p.major_stars.map { s -> s.name + (transforms[s.name]?.transformation?.removePrefix("化")?.let { "【$it】" } ?: "") },
                    p.auxiliary_stars.map { s -> s.name + (transforms[s.name]?.transformation?.removePrefix("化")?.let { "【$it】" } ?: "") },
                    buildList { if (p.is_life_palace) add("【命】"); if (p.has_body_palace) add("【身】") },
                    ages[p.earthly_branch]?.let { "${it.start_nominal_age}–${it.end_nominal_age}" } ?: "",
                )
            },
        )
    }
}
