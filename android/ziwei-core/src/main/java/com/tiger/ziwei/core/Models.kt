package com.tiger.ziwei.core

data class BirthInput(
    val name: String? = null,
    val gender: String,
    val calendar_type: String = "solar",
    val birth_year: Int? = null,
    val birth_month: Int? = null,
    val birth_day: Int? = null,
    val lunar_year: Int? = null,
    val lunar_month: Int? = null,
    val lunar_day: Int? = null,
    val is_leap_month: Boolean? = null,
    val birth_hour: Int,
    val birth_minute: Int,
    val birthplace: String,
)

data class BirthData(
    val name: String? = null,
    val gender: String,
    val birth_year: Int,
    val birth_month: Int,
    val birth_day: Int,
    val birth_hour: Int,
    val birth_minute: Int,
    val birthplace: String,
)

data class LunarDateResult(
    val year: Int,
    val month: Int,
    val day: Int,
    val is_leap_month: Boolean,
)

data class GanzhiResult(val heavenly_stem: String, val earthly_branch: String) {
    val display: String get() = heavenly_stem + earthly_branch
}

data class CalendarResult(
    val solar_date: String,
    val solar_time: String,
    val lunar_date: LunarDateResult,
    val year_ganzhi: GanzhiResult,
    val month_ganzhi: GanzhiResult,
    val day_ganzhi: GanzhiResult,
    val hour_ganzhi: GanzhiResult,
    val year_boundary: String = "lunar_new_year",
    val month_boundary: String = "solar_term_civil_date",
    val day_boundary: String = "civil_midnight",
    val hour_policy: String = "civil_day_stem_no_23h_rollover",
    val time_basis: String = "supplied_civil_standard_time",
)

data class PalacePosition(
    val name: String,
    val earthly_branch: String,
    val has_body_palace: Boolean,
    val is_life_palace: Boolean,
)

data class PalaceLayout(
    val effective_lunar_month: Int,
    val birth_hour_branch: String,
    val palaces: List<PalacePosition>,
    val life_palace_branch: String,
    val body_palace_branch: String,
    val body_palace_name: String,
)

data class StarPlacement(val name: String, val earthly_branch: String)

data class BureauResult(
    val year_heavenly_stem: String,
    val yin_palace_heavenly_stem: String,
    val life_palace_ganzhi: GanzhiResult,
    val nayin_element: String,
    val life_palace_heavenly_stem: String,
    val life_palace_earthly_branch: String,
    val bureau_name: String,
    val bureau_number: Int,
)

data class MajorStarChart(
    val lunar_day: Int,
    val bureau_element: String,
    val stars: List<StarPlacement>,
    val bureau_name: String,
    val bureau_number: Int,
    val ziwei_branch: String,
    val tianfu_branch: String,
)

data class AuxiliaryStarChart(val status: String = "PASS", val stars: List<StarPlacement>)

data class Transformation(
    val transformation: String,
    val star_name: String,
    val earthly_branch: String,
    val palace_name: String,
    val star_category: String,
)

data class BirthYearTransformations(
    val year_heavenly_stem: String,
    val transformations: List<Transformation>,
)

data class Palace(
    val palace_name: String,
    val palace_ganzhi: GanzhiResult,
    val has_body_palace: Boolean,
    val major_stars: List<StarPlacement>,
    val auxiliary_stars: List<StarPlacement>,
    val earthly_branch: String,
    val heavenly_stem: String,
    val is_life_palace: Boolean,
)

data class LocatedTransformation(
    val transformation_type: String,
    val star_name: String,
    val star_category: String,
    val earthly_branch: String,
    val natal_palace_name: String,
)

data class FlowPeriodTransformation(
    val transformation_type: String,
    val star_name: String,
    val star_category: String,
    val natal_branch: String,
    val natal_palace_name: String,
)

data class MajorLuckPeriod(
    val index: Int,
    val start_nominal_age: Int,
    val end_nominal_age: Int,
    val earthly_branch: String,
    val palace_name: String,
    val heavenly_stem: String,
    val palace_ganzhi: GanzhiResult,
)

data class MajorLuckPeriodTransformations(
    val major_luck_index: Int,
    val start_nominal_age: Int,
    val end_nominal_age: Int,
    val major_luck_heavenly_stem: String,
    val major_luck_earthly_branch: String,
    val major_luck_palace_name: String,
    val transformations: List<LocatedTransformation>,
)

data class MajorLuckResult(
    val bureau_name: String,
    val bureau_number: Int,
    val year_heavenly_stem: String,
    val year_yinyang: String,
    val gender: String,
    val direction: String,
    val periods: List<MajorLuckPeriod>,
    val period_transformations: List<MajorLuckPeriodTransformations>,
)

data class BasicChartResult(
    val birth_data: BirthData,
    val calendar: CalendarResult,
    val palace_layout: PalaceLayout,
    val five_elements_bureau: BureauResult,
    val major_star_chart: MajorStarChart,
    val auxiliary_star_chart: AuxiliaryStarChart,
    val birth_year_transformations: BirthYearTransformations,
    val palaces: List<Palace>,
    val major_luck: MajorLuckResult,
    val life_palace_branch: String,
    val body_palace_branch: String,
    val body_palace_name: String,
)

data class FlowYearPalace(
    val flow_palace_name: String,
    val earthly_branch: String,
    val natal_palace_name: String,
    val natal_palace_heavenly_stem: String,
    val natal_palace_ganzhi: GanzhiResult,
)

data class FlowPeriodPalace(
    val flow_palace_name: String,
    val earthly_branch: String,
    val natal_palace_name: String,
    val natal_palace_ganzhi: GanzhiResult,
)

data class FlowYearResult(
    val target_lunar_year: Int,
    val heavenly_stem: String,
    val earthly_branch: String,
    val ganzhi: GanzhiResult,
    val nominal_age: Int,
    val flow_life_palace_branch: String,
    val palaces: List<FlowYearPalace>,
    val transformations: List<LocatedTransformation>,
    val active_major_luck: MajorLuckPeriod?,
    val before_first_major_luck: Boolean,
    val after_supported_major_luck: Boolean,
)

data class FlowMonthResult(
    val lunar_year: Int,
    val lunar_month: Int,
    val is_leap_month: Boolean,
    val effective_month: Int,
    val month_ganzhi: GanzhiResult,
    val flow_month_life_palace_branch: String,
    val natal_host_palace_name: String,
    val natal_host_palace_ganzhi: GanzhiResult,
    val palaces: List<FlowPeriodPalace>,
    val transformations: List<FlowPeriodTransformation>,
)

data class FlowDayResult(
    val target_lunar_year: Int,
    val target_lunar_month: Int,
    val target_lunar_day: Int,
    val target_is_leap_month: Boolean,
    val day_ganzhi: GanzhiResult,
    val flow_day_life_palace_branch: String,
    val natal_host_palace_name: String,
    val natal_host_palace_ganzhi: GanzhiResult,
    val palaces: List<FlowPeriodPalace>,
    val transformations: List<FlowPeriodTransformation>,
)

data class FlowQueryInput(
    val mode: String,
    val year: Int,
    val month: Int? = null,
    val day: Int? = null,
    val is_leap_month: Boolean = false,
)

data class SolarFlowQuery(val mode: String = "solar", val year: Int, val month: Int, val day: Int)
data class LunarFlowQuery(
    val mode: String = "lunar",
    val year: Int,
    val month: Int? = null,
    val day: Int? = null,
    val is_leap_month: Boolean = false,
)

data class NormalizedFlowTarget(
    val input_mode: String,
    val original_solar_date: String? = null,
    val original_lunar_year: Int? = null,
    val original_lunar_month: Int? = null,
    val original_lunar_day: Int? = null,
    val original_is_leap_month: Boolean? = null,
    val converted_solar_date: String? = null,
    val lunar_year: Int,
    val lunar_month: Int? = null,
    val lunar_day: Int? = null,
    val is_leap_month: Boolean,
    val effective_month: Int? = null,
)

data class FlowQueryResult(
    val query_mode: String,
    val original_query: Any,
    val normalized_target: NormalizedFlowTarget,
    val flow_year: FlowYearResult,
    val flow_month: FlowMonthResult? = null,
    val flow_day: FlowDayResult? = null,
)
