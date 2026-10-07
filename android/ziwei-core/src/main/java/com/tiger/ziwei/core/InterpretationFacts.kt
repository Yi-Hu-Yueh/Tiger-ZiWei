package com.tiger.ziwei.core

import com.google.gson.JsonArray
import com.google.gson.JsonElement
import com.google.gson.JsonObject

/** Builds the exact deterministic payloads supplied to the five AI scopes. */
object InterpretationFacts {
    private fun palaceFacts(chart: BasicChartResult): JsonArray {
        val byBranch = chart.birth_year_transformations.transformations.groupBy { it.earthly_branch }
        return JsonArray().apply {
            chart.palaces.forEach { palace ->
                add(JsonObject().apply {
                    addProperty("palace_name", palace.palace_name)
                    addProperty("earthly_branch", palace.earthly_branch)
                    add("palace_ganzhi", ZiweiCore.gson.toJsonTree(palace.palace_ganzhi))
                    addProperty("is_life_palace", palace.is_life_palace)
                    addProperty("has_body_palace", palace.has_body_palace)
                    add("major_stars", names(palace.major_stars))
                    add("auxiliary_stars", names(palace.auxiliary_stars))
                    add("birth_year_transformations", ZiweiCore.gson.toJsonTree(byBranch[palace.earthly_branch].orEmpty()))
                })
            }
        }
    }

    private fun names(stars: List<StarPlacement>) = JsonArray().apply {
        stars.forEach { add(it.name) }
    }

    private fun common(chart: BasicChartResult): JsonObject = JsonObject().apply {
        add("birth_data", ZiweiCore.gson.toJsonTree(chart.birth_data))
        addProperty("gender", chart.birth_data.gender)
        add("lunar_date", ZiweiCore.gson.toJsonTree(chart.calendar.lunar_date))
        add("year_ganzhi", ZiweiCore.gson.toJsonTree(chart.calendar.year_ganzhi))
        add("month_ganzhi", ZiweiCore.gson.toJsonTree(chart.calendar.month_ganzhi))
        add("day_ganzhi", ZiweiCore.gson.toJsonTree(chart.calendar.day_ganzhi))
        add("hour_ganzhi", ZiweiCore.gson.toJsonTree(chart.calendar.hour_ganzhi))
        addProperty("life_palace_branch", chart.life_palace_branch)
        addProperty("body_palace_branch", chart.body_palace_branch)
        addProperty("body_palace_name", chart.body_palace_name)
        addProperty("bureau_name", chart.five_elements_bureau.bureau_name)
        addProperty("bureau_number", chart.five_elements_bureau.bureau_number)
        add("palaces", palaceFacts(chart))
        add("birth_year_transformations", ZiweiCore.gson.toJsonTree(chart.birth_year_transformations.transformations))
    }

    fun natal(chart: BasicChartResult): JsonObject = JsonObject().apply {
        val birth = chart.birth_data
        add("birth", JsonObject().apply {
            if (birth.name == null) add("name", com.google.gson.JsonNull.INSTANCE) else addProperty("name", birth.name)
            addProperty("gender", birth.gender)
            addProperty("gregorian_date", chart.calendar.solar_date)
            addProperty("supplied_civil_time", "%02d:%02d".format(java.util.Locale.ROOT, birth.birth_hour, birth.birth_minute))
            addProperty("birthplace", birth.birthplace)
        })
        add("calendar", JsonObject().apply {
            add("lunar_date", ZiweiCore.gson.toJsonTree(chart.calendar.lunar_date))
            addProperty("effective_natal_month", chart.palace_layout.effective_lunar_month)
            addProperty("year_ganzhi", chart.calendar.year_ganzhi.display)
            addProperty("month_ganzhi", chart.calendar.month_ganzhi.display)
            addProperty("day_ganzhi", chart.calendar.day_ganzhi.display)
            addProperty("hour_ganzhi", chart.calendar.hour_ganzhi.display)
        })
        add("core", JsonObject().apply {
            addProperty("life_palace_branch", chart.life_palace_branch)
            addProperty("body_palace_branch", chart.body_palace_branch)
            addProperty("body_palace_host", chart.body_palace_name)
            addProperty("five_elements_bureau", chart.five_elements_bureau.bureau_name)
        })
        val birthByBranch = chart.birth_year_transformations.transformations.groupBy { it.earthly_branch }
        add("palaces", JsonArray().apply {
            chart.palaces.forEach { palace ->
                add(JsonObject().apply {
                    addProperty("palace_name", palace.palace_name)
                    addProperty("earthly_branch", palace.earthly_branch)
                    addProperty("palace_ganzhi", palace.palace_ganzhi.display)
                    addProperty("is_life_palace", palace.is_life_palace)
                    addProperty("has_body_palace", palace.has_body_palace)
                    add("major_stars", names(palace.major_stars))
                    add("auxiliary_stars", names(palace.auxiliary_stars))
                    add("birth_year_transformations", ZiweiCore.gson.toJsonTree(birthByBranch[palace.earthly_branch].orEmpty()))
                })
            }
        })
        add("birth_year_transformations", ZiweiCore.gson.toJsonTree(chart.birth_year_transformations.transformations))
    }

    fun majorLuck(chart: BasicChartResult, index: Int): JsonObject {
        require(index in 1..12)
        val result = common(chart)
        val period = chart.major_luck.periods[index - 1]
        val transformations = chart.major_luck.period_transformations[index - 1]
        result.addProperty("direction", chart.major_luck.direction)
        result.add("selected_major_luck", ZiweiCore.gson.toJsonTree(period))
        result.add("major_luck_transformations", ZiweiCore.gson.toJsonTree(transformations.transformations))
        return result
    }

    fun flowYear(chart: BasicChartResult, flow: FlowYearResult): JsonObject {
        val result = common(chart)
        result.addProperty("major_luck_direction", chart.major_luck.direction)
        result.add("active_major_luck", ZiweiCore.gson.toJsonTree(flow.active_major_luck))
        val active = flow.active_major_luck?.let { period ->
            chart.major_luck.period_transformations.firstOrNull { it.major_luck_index == period.index }?.transformations
        }.orEmpty()
        result.add("active_major_luck_transformations", ZiweiCore.gson.toJsonTree(active))
        result.addProperty("before_first_major_luck", flow.before_first_major_luck)
        result.addProperty("after_supported_major_luck", flow.after_supported_major_luck)
        result.add("flow_year", ZiweiCore.gson.toJsonTree(flow))
        return result
    }

    fun flowMonth(chart: BasicChartResult, flowYear: FlowYearResult, month: FlowMonthResult): JsonObject =
        JsonObject().apply {
            add("flow_year_facts", flowYear(chart, flowYear))
            add("flow_month", ZiweiCore.gson.toJsonTree(month))
        }

    fun flowDay(
        chart: BasicChartResult,
        flowYear: FlowYearResult,
        month: FlowMonthResult,
        day: FlowDayResult,
    ): JsonObject = JsonObject().apply {
        add("flow_year_facts", flowYear(chart, flowYear))
        add("flow_month", ZiweiCore.gson.toJsonTree(month))
        add("flow_day", ZiweiCore.gson.toJsonTree(day))
    }
}
