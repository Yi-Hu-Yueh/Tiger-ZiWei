package com.tiger.ziwei.core

import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.ByteArrayInputStream
import java.util.zip.ZipInputStream
import javax.xml.parsers.DocumentBuilderFactory

class DocxReportTest {
    private val chart = ZiweiCore.calculateChart(BirthInput("Tiger", "female", birth_year = 2025, birth_month = 1, birth_day = 29, birth_hour = 0, birth_minute = 30, birthplace = "Taipei"))

    @Test fun validPackageContainsImageTablesAndChinese() {
        val png = java.util.Base64.getDecoder().decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jk1sAAAAASUVORK5CYII=")
        val flow = ZiweiCore.calculateFlowQuery(chart, FlowQueryInput("solar", 2029, 2, 13))
        val responses = listOf("natal", "major_luck", "flow_year", "flow_month", "flow_day").associateWith { scope ->
            AiPolicy.parseProviderJson(javaClass.classLoader!!.getResourceAsStream("mock_$scope.json")!!.bufferedReader(Charsets.UTF_8).use { it.readText() })
        }
        val bytes = DocxReport.generate(chart, png, flow, responses)
        val file = java.io.File("build/reports/standalone/representative.docx")
        file.parentFile.mkdirs(); file.writeBytes(bytes)
        val entries = linkedMapOf<String, ByteArray>()
        ZipInputStream(ByteArrayInputStream(bytes)).use { zip ->
            while (true) { val e = zip.nextEntry ?: break; entries[e.name] = zip.readBytes() }
        }
        listOf("[Content_Types].xml", "_rels/.rels", "word/document.xml", "word/_rels/document.xml.rels", "word/styles.xml", "word/media/chart.png").forEach { assertTrue(it in entries) }
        listOf("[Content_Types].xml", "_rels/.rels", "word/document.xml", "word/_rels/document.xml.rels", "word/styles.xml").forEach {
            DocumentBuilderFactory.newInstance().newDocumentBuilder().parse(ByteArrayInputStream(entries.getValue(it)))
        }
        val doc = entries.getValue("word/document.xml").toString(Charsets.UTF_8)
        listOf("出生資料", "本命命盤圖", "本命十二宮", "生年四化", "完整大限", "Tiger-ZiWei", "流年 2029", "流月 1", "流日 1", "流年四化", "流月四化", "流日四化", "本命 AI 解讀", "大限 AI 解讀", "流年 AI 解讀", "流月 AI 解讀", "流日 AI 解讀").forEach { assertTrue(it, doc.contains(it)) }
        assertTrue(doc.contains("<w:tbl>"))
        org.junit.Assert.assertArrayEquals(png, entries.getValue("word/media/chart.png"))
    }

    @Test fun filenamePreservesFlowGranularityAndLeapMonth() {
        val q = ZiweiCore.calculateFlowQuery(chart, FlowQueryInput("lunar", 2025, 6, 1, true))
        assertTrue(DocxReport.filename(chart, q).endsWith("_流年2025-流月閏6-流日1.docx"))
    }
}
