package com.tiger.ziwei.core

import com.google.gson.JsonParser
import org.junit.Assert.assertEquals
import org.junit.Test

class GoldenParityTest {
    private fun fixture(name: String) = javaClass.classLoader!!
        .getResourceAsStream(name)!!.bufferedReader(Charsets.UTF_8).use { it.readText() }

    private fun assertJson(name: String, actual: Any) {
        assertEquals(name, JsonParser.parseString(fixture(name)), ZiweiCore.gson.toJsonTree(actual))
    }

    private val cases = mapOf(
        "A" to BirthInput("Case A", "female", birth_year = 2025, birth_month = 1, birth_day = 29, birth_hour = 0, birth_minute = 30, birthplace = "Taipei"),
        "B" to BirthInput("Case B", "female", birth_year = 2025, birth_month = 1, birth_day = 29, birth_hour = 1, birth_minute = 30, birthplace = "Taipei"),
        "C" to BirthInput("Case C", "female", birth_year = 2024, birth_month = 2, birth_day = 29, birth_hour = 12, birth_minute = 0, birthplace = "Taipei"),
        "L" to BirthInput("Case L", "female", birth_year = 2025, birth_month = 7, birth_day = 25, birth_hour = 12, birth_minute = 0, birthplace = "Taipei"),
        "Z" to BirthInput("Case Z", "female", birth_year = 2025, birth_month = 7, birth_day = 24, birth_hour = 23, birth_minute = 59, birthplace = "Taipei"),
        "A_male" to BirthInput("Case A Male", "male", birth_year = 2025, birth_month = 1, birth_day = 29, birth_hour = 0, birth_minute = 30, birthplace = "Taipei"),
    )

    @Test fun natalGoldenParity() {
        cases.forEach { (name, input) -> assertJson("natal_$name.json", ZiweiCore.calculateChart(input)) }
    }

    @Test fun flowYearGoldenParity() {
        val female = ZiweiCore.calculateChart(cases.getValue("A"))
        listOf(2026, 2029, 2032, 2039).forEach { year ->
            assertJson("flow_year_A_$year.json", ZiweiCore.flowYear(female, year))
        }
        val male = ZiweiCore.calculateChart(cases.getValue("A_male"))
        assertJson("flow_year_A_male_2039.json", ZiweiCore.flowYear(male, 2039))
    }

    @Test fun flowQueryGoldenParity() {
        val chart = ZiweiCore.calculateChart(cases.getValue("A"))
        val queries = linkedMapOf(
            "solar_2029_02_12" to FlowQueryInput("solar", 2029, 2, 12),
            "solar_2029_02_13" to FlowQueryInput("solar", 2029, 2, 13),
            "lunar_2026_year" to FlowQueryInput("lunar", 2026),
            "lunar_2026_month10" to FlowQueryInput("lunar", 2026, 10),
            "lunar_2026_month10_day7" to FlowQueryInput("lunar", 2026, 10, 7),
            "solar_2025_07_25" to FlowQueryInput("solar", 2025, 7, 25),
            "lunar_2025_leap6_day1" to FlowQueryInput("lunar", 2025, 6, 1, true),
        )
        queries.forEach { (name, query) ->
            assertJson("flow_query_A_$name.json", ZiweiCore.calculateFlowQuery(chart, query))
        }
    }

    @Test fun transformationTableParity() {
        assertEquals(
            JsonParser.parseString(fixture("transformation_targets.json")),
            ZiweiCore.gson.toJsonTree(TRANSFORMATION_TARGETS_BY_STEM),
        )
    }

    @Test fun allFiveBureauStartAgesParity() {
        assertJson("bureau_start_ages.json", BUREAU_START_AGES)
    }

    @Test fun interpretationFactPayloadParity() {
        val chart = ZiweiCore.calculateChart(cases.getValue("A"))
        val query = ZiweiCore.calculateFlowQuery(chart, FlowQueryInput("solar", 2029, 2, 13))
        val month = requireNotNull(query.flow_month)
        val day = requireNotNull(query.flow_day)
        assertJson("interpretation_facts_natal.json", InterpretationFacts.natal(chart))
        assertJson("interpretation_facts_major_luck.json", InterpretationFacts.majorLuck(chart, 5))
        assertJson("interpretation_facts_flow_year.json", InterpretationFacts.flowYear(chart, query.flow_year))
        assertJson("interpretation_facts_flow_month.json", InterpretationFacts.flowMonth(chart, query.flow_year, month))
        assertJson("interpretation_facts_flow_day.json", InterpretationFacts.flowDay(chart, query.flow_year, month, day))
    }
}
