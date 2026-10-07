package com.tiger.ziwei.core

import org.junit.Assert.*
import org.junit.Test

class InputCodecTest {
    private val birth = """{"gender":"female","birth_year":2025,"birth_month":1,"birth_day":29,"birth_hour":0,"birth_minute":30,"birthplace":"Taipei"}"""

    @Test fun optionalCalendarModeDefaultsAndRequiredTimeNeverDefaults() {
        assertEquals("solar", InputCodec.birth(birth).calendar_type)
        assertEquals(2025, ZiweiCore.calculateChart(InputCodec.birth(birth)).birth_data.birth_year)
        val locale = java.util.Locale.getDefault()
        try {
            java.util.Locale.setDefault(java.util.Locale.forLanguageTag("ar-EG"))
            val chart = ZiweiCore.calculateChart(InputCodec.birth(birth))
            assertEquals("00:30:00", chart.calendar.solar_time)
            assertEquals("2025-01-29_0030_紫微斗數命盤.docx", DocxReport.filename(chart, null))
            assertEquals("00:30", InterpretationFacts.natal(chart)["birth"].asJsonObject["supplied_civil_time"].asString)
        } finally { java.util.Locale.setDefault(locale) }
        assertThrows(IllegalArgumentException::class.java) { InputCodec.birth(birth.replace("\"birth_hour\":0,", "")) }
        assertThrows(IllegalArgumentException::class.java) { InputCodec.birth(birth.replace("\"birth_hour\":0", "\"birth_hour\":true")) }
    }

    @Test fun invalidModeLeapPairAndPrebirthQueriesAreRejected() {
        assertThrows(IllegalArgumentException::class.java) { TigerCalendar.normalizeBirth(InputCodec.birth(birth.replace("\"gender\":", "\"calendar_type\":\"wrong\",\"gender\":"))) }
        val chart = ZiweiCore.calculateChart(InputCodec.birth(birth))
        assertThrows(IllegalArgumentException::class.java) { ZiweiCore.calculateFlowQuery(chart, FlowQueryInput("lunar", 2026, is_leap_month = true)) }
        assertThrows(IllegalArgumentException::class.java) { ZiweiCore.calculateFlowQuery(chart, FlowQueryInput("solar", 2024, 1, 1)) }
    }
}
