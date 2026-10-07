package com.tiger.ziwei.core

import com.google.gson.JsonObject
import org.junit.Assert.assertThrows
import org.junit.Test

class FactLockTest {
    private val chart = ZiweiCore.calculateChart(BirthInput("Case A", "female", birth_year = 2025, birth_month = 1, birth_day = 29, birth_hour = 0, birth_minute = 30, birthplace = "Taipei"))
    private val query = ZiweiCore.calculateFlowQuery(chart, FlowQueryInput("solar", 2029, 2, 13))

    private fun valid(scope: String, facts: JsonObject): JsonObject = AiPolicy.outputContract(scope, facts).deepCopy().also { result ->
        fun replace(e: com.google.gson.JsonElement) {
            when {
                e.isJsonArray -> e.asJsonArray.forEach(::replace)
                e.isJsonObject -> e.asJsonObject.entrySet().forEach { (key, value) ->
                    if (value.isJsonPrimitive && value.asJsonPrimitive.isString && value.asString.contains("繁體中文")) e.asJsonObject.addProperty(key, "此為謹慎解讀。") else replace(value)
                }
            }
        }
        replace(result)
    }

    @Test fun acceptsAllFiveValidScopes() {
        val month = query.flow_month!!; val day = query.flow_day!!
        val cases = listOf(
            "natal" to InterpretationFacts.natal(chart),
            "major_luck" to InterpretationFacts.majorLuck(chart, 5),
            "flow_year" to InterpretationFacts.flowYear(chart, query.flow_year),
            "flow_month" to InterpretationFacts.flowMonth(chart, query.flow_year, month),
            "flow_day" to InterpretationFacts.flowDay(chart, query.flow_year, month, day),
        )
        cases.forEach { (scope, facts) ->
            val raw = javaClass.classLoader!!.getResourceAsStream("mock_$scope.json")!!.bufferedReader(Charsets.UTF_8).use { it.readText() }
            AiPolicy.validate(scope, facts, AiPolicy.parseProviderJson(raw))
        }
    }

    @Test fun rejectsChangedAnchorsAndTransformations() {
        val monthFacts = InterpretationFacts.flowMonth(chart, query.flow_year, query.flow_month!!)
        valid("flow_month", monthFacts).also { it.addProperty("natal_host_palace", "命宮") }.let {
            assertThrows(IllegalArgumentException::class.java) { AiPolicy.validate("flow_month", monthFacts, it) }
        }
        val yearFacts = InterpretationFacts.flowYear(chart, query.flow_year)
        valid("flow_year", yearFacts).also { it.addProperty("nominal_age", 99) }.let {
            assertThrows(IllegalArgumentException::class.java) { AiPolicy.validate("flow_year", yearFacts, it) }
        }
        val majorFacts = InterpretationFacts.majorLuck(chart, 5)
        valid("major_luck", majorFacts).also { it["transformation_analysis"].asJsonArray[2].asJsonObject.addProperty("star_name", "左輔") }.let {
            assertThrows(IllegalArgumentException::class.java) { AiPolicy.validate("major_luck", majorFacts, it) }
        }
    }

    @Test fun rejectsMissingDuplicateWrongLayerAndExactHour() {
        val facts = InterpretationFacts.flowDay(chart, query.flow_year, query.flow_month!!, query.flow_day!!)
        valid("flow_day", facts).also { it["transformation_analysis"].asJsonArray.remove(3) }.let {
            assertThrows(IllegalArgumentException::class.java) { AiPolicy.validate("flow_day", facts, it) }
        }
        valid("flow_day", facts).also { val a = it["transformation_analysis"].asJsonArray; a.set(1, a[0].deepCopy()) }.let {
            assertThrows(IllegalArgumentException::class.java) { AiPolicy.validate("flow_day", facts, it) }
        }
        valid("flow_day", facts).also { it.addProperty("lunar_month", 12) }.let {
            assertThrows(IllegalArgumentException::class.java) { AiPolicy.validate("flow_day", facts, it) }
        }
        valid("flow_day", facts).also { it.addProperty("overview", "下午 3 點一定有事") }.let {
            assertThrows(IllegalArgumentException::class.java) { AiPolicy.validate("flow_day", facts, it) }
        }
    }

    @Test fun rejectsMalformedSchemaAndAlteredGanzhi() {
        val facts = InterpretationFacts.flowYear(chart, query.flow_year)
        valid("flow_year", facts).also { it["flow_year_ganzhi"].asJsonObject.addProperty("heavenly_stem", "甲") }.let {
            assertThrows(IllegalArgumentException::class.java) { AiPolicy.validate("flow_year", facts, it) }
        }
        valid("flow_year", facts).also { it.remove("career") }.let {
            assertThrows(IllegalArgumentException::class.java) { AiPolicy.validate("flow_year", facts, it) }
        }
        valid("flow_year", facts).also { it.addProperty("overview", "   ") }.let {
            assertThrows(IllegalArgumentException::class.java) { AiPolicy.validate("flow_year", facts, it) }
        }
        valid("flow_year", facts).also { it.addProperty("reasoning_content", "should never be shown") }.let {
            assertThrows(IllegalArgumentException::class.java) { AiPolicy.validate("flow_year", facts, it) }
        }
    }

    @Test fun beforeFirstMajorLuckAcceptsPythonOptionalNullDefaults() {
        val facts = InterpretationFacts.flowYear(chart, ZiweiCore.flowYear(chart, 2026))
        val response = valid("flow_year", facts)
        val summary = response["active_major_luck_summary"].asJsonObject
        summary.keySet().toList().filter { it != "status" }.forEach { summary.remove(it) }
        AiPolicy.validate("flow_year", facts, response)
        org.junit.Assert.assertTrue(summary["major_luck_index"].isJsonNull)
        org.junit.Assert.assertEquals("before_first_major_luck", summary["status"].asString)
    }
}
