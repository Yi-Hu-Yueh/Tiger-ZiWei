package com.tiger.ziwei

import com.google.gson.JsonParser
import com.tiger.ziwei.core.ZiweiCore
import org.junit.Assert.*
import org.junit.Test

class StandaloneServiceTest {
    private val service = StandaloneService()
    private val birth = """{"name":"Case A","gender":"female","calendar_type":"solar","birth_year":2025,"birth_month":1,"birth_day":29,"birth_hour":0,"birth_minute":30,"birthplace":"Taipei"}"""
    private fun envelope(body: String, headers: Map<String, String> = emptyMap()) = ZiweiCore.gson.toJson(mapOf("body" to body, "headers" to headers))

    @Test fun localModelRegistryAndCalculationsNeedNoAndroidContextOrNetwork() {
        val models = JsonParser.parseString(service.execute("get_models", envelope(""))).asJsonArray
        assertEquals(2, models.size())
        assertTrue(models[0].asJsonObject["default"].asBoolean)
        val chart = JsonParser.parseString(service.execute("calculate_chart", envelope(birth))).asJsonObject
        assertEquals("寅", chart["life_palace_branch"].asString)
        val request = """{"birth_input":$birth,"query":{"mode":"solar","year":2029,"month":2,"day":13}}"""
        val flow = JsonParser.parseString(service.execute("calculate_flow_query", envelope(request))).asJsonObject
        assertEquals(2029, flow["flow_year"].asJsonObject["target_lunar_year"].asInt)
        assertFalse(flow["flow_month"].isJsonNull)
        assertFalse(flow["flow_day"].isJsonNull)
    }

    @Test fun blankKeyAndUnknownActionAreRejectedWithoutNetwork() {
        val error = assertThrows(StandaloneException::class.java) { service.execute("interpret_natal", envelope(birth)) }
        assertEquals("請輸入 NVIDIA API KEY。", error.message)
        assertThrows(IllegalArgumentException::class.java) { service.execute("execute_shell", envelope("")) }
        assertThrows(IllegalArgumentException::class.java) { service.execute("interpret_natal", envelope(birth, mapOf("X-Tiger-NVIDIA-API-Key" to "mock-unused-key", "X-Tiger-NVIDIA-Model" to "unknown/model"))) }
    }
}
