package com.tiger.ziwei.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ChartRenderStructureTest {
    @Test fun approvedSquareLayoutContainsAllRequiredSemanticData() {
        val chart = ZiweiCore.calculateChart(BirthInput("Case A", "female", birth_year = 2025, birth_month = 1, birth_day = 29, birth_hour = 0, birth_minute = 30, birthplace = "Taipei"))
        val data = ChartRenderData.from(chart)
        assertEquals(1648, data.width); assertEquals(1648, data.height); assertEquals(12, data.cells.size)
        assertEquals(EARTHLY_BRANCHES.toSet(), data.cells.map { it.branch }.toSet())
        assertEquals(PALACE_ORDER.toSet(), data.cells.map { it.palace }.toSet())
        assertEquals(14, data.cells.sumOf { it.majorStars.size }); assertEquals(14, data.cells.sumOf { it.auxiliaryStars.size })
        val text = data.cells.flatMap { it.majorStars + it.auxiliaryStars + it.markers }.joinToString()
        listOf("【命】", "【身】", "【祿】", "【權】", "【科】", "【忌】").forEach { assertTrue(text.contains(it)) }
        assertTrue(data.cells.all { it.majorLuckAge.isNotBlank() })
    }
}
