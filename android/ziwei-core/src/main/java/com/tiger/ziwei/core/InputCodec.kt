package com.tiger.ziwei.core

import com.google.gson.JsonObject
import com.google.gson.JsonParser

/** Validate untrusted bridge input before Gson can bypass Kotlin constructor defaults. */
object InputCodec {
    private fun integer(obj: JsonObject, key: String, optional: Boolean = false): Int? {
        val e = obj[key]
        if (optional && (e == null || e.isJsonNull)) return null
        require(e != null && e.isJsonPrimitive && e.asJsonPrimitive.isNumber) { "$key 必須是整數。" }
        val n = e.asBigDecimal
        require(n.stripTrailingZeros().scale() <= 0) { "$key 必須是整數。" }
        return n.intValueExact()
    }
    private fun text(obj: JsonObject, key: String, optional: Boolean = false): String? {
        val e = obj[key]
        if (optional && (e == null || e.isJsonNull)) return null
        require(e != null && e.isJsonPrimitive && e.asJsonPrimitive.isString) { "$key 必須是文字。" }
        return e.asString
    }
    private fun bool(obj: JsonObject, key: String): Boolean? {
        val e = obj[key] ?: return null
        if (e.isJsonNull) return null
        require(e.isJsonPrimitive && e.asJsonPrimitive.isBoolean) { "$key 必須是布林值。" }
        return e.asBoolean
    }

    fun birth(raw: String): BirthInput {
        val o = JsonParser.parseString(raw).asJsonObject
        require(o.keySet().all { it in setOf("name", "gender", "calendar_type", "birth_year", "birth_month", "birth_day", "lunar_year", "lunar_month", "lunar_day", "is_leap_month", "birth_hour", "birth_minute", "birthplace") }) { "出生資料包含未知欄位。" }
        return BirthInput(
            name = text(o, "name", true), gender = requireNotNull(text(o, "gender")),
            calendar_type = text(o, "calendar_type", true) ?: "solar",
            birth_year = integer(o, "birth_year", true), birth_month = integer(o, "birth_month", true), birth_day = integer(o, "birth_day", true),
            lunar_year = integer(o, "lunar_year", true), lunar_month = integer(o, "lunar_month", true), lunar_day = integer(o, "lunar_day", true), is_leap_month = bool(o, "is_leap_month"),
            birth_hour = requireNotNull(integer(o, "birth_hour")), birth_minute = requireNotNull(integer(o, "birth_minute")), birthplace = requireNotNull(text(o, "birthplace")),
        )
    }

    fun query(o: JsonObject): FlowQueryInput {
        val mode = requireNotNull(text(o, "mode"))
        require(mode in setOf("solar", "lunar"))
        val fields = if (mode == "solar") setOf("mode", "year", "month", "day") else setOf("mode", "year", "month", "day", "is_leap_month")
        require(o.keySet().all { it in fields }) { "運限查詢包含未知欄位。" }
        return FlowQueryInput(mode, requireNotNull(integer(o, "year")), integer(o, "month", mode == "lunar"), integer(o, "day", mode == "lunar"), bool(o, "is_leap_month") ?: false)
    }
}
