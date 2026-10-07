package com.tiger.ziwei.core

import com.google.gson.JsonElement
import com.google.gson.JsonObject
import java.io.ByteArrayOutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

/** Small deterministic OOXML writer containing only features used by Tiger-ZiWei. */
object DocxReport {
    const val MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    fun filename(chart: BasicChartResult, flow: FlowQueryResult?): String {
        val birth = chart.birth_data
        val name = birth.name?.takeIf { it.isNotBlank() } ?: "%04d-%02d-%02d_%02d%02d".format(java.util.Locale.ROOT, birth.birth_year, birth.birth_month, birth.birth_day, birth.birth_hour, birth.birth_minute)
        val base = sanitize(name) + "_紫微斗數命盤"
        val target = flow?.normalized_target ?: return "$base.docx"
        val year = target.lunar_year
        val month = target.lunar_month
        val day = target.lunar_day
        val suffix = buildString {
            append("_流年").append(year)
            if (month != null) append("-流月").append(if (target.is_leap_month) "閏" else "").append(month)
            if (day != null) append("-流日").append(day)
        }
        return "$base$suffix.docx"
    }

    private fun sanitize(value: String) = value.replace(Regex("[\\\\/:*?\"<>|\\x00-\\x1f]"), "_").trim(' ', '.').take(120).ifBlank { "Tiger-ZiWei" }

    fun generate(
        chart: BasicChartResult,
        chartPng: ByteArray,
        flow: FlowQueryResult? = null,
        interpretations: Map<String, JsonObject> = emptyMap(),
    ): ByteArray {
        val body = StringBuilder()
        body.heading("Tiger-ZiWei 紫微斗數命盤", 1)
        body.heading("出生資料", 2)
        body.table(listOf("欄位", "內容"), listOf(
            listOf("姓名", chart.birth_data.name ?: "未填"), listOf("性別", if (chart.birth_data.gender == "female") "女" else "男"),
            listOf("國曆", "${chart.calendar.solar_date} ${chart.calendar.solar_time}"),
            listOf("農曆", "${chart.calendar.lunar_date.year} 年${if (chart.calendar.lunar_date.is_leap_month) "閏" else ""}${chart.calendar.lunar_date.month} 月 ${chart.calendar.lunar_date.day} 日"),
            listOf("出生地", chart.birth_data.birthplace), listOf("四柱", "${chart.calendar.year_ganzhi.display}　${chart.calendar.month_ganzhi.display}　${chart.calendar.day_ganzhi.display}　${chart.calendar.hour_ganzhi.display}"),
            listOf("命宮／身宮", "${chart.life_palace_branch}／${chart.body_palace_branch}（${chart.body_palace_name}）"),
            listOf("五行局", chart.five_elements_bureau.bureau_name),
        ))
        body.heading("本命命盤圖", 2)
        body.append("<w:p><w:r><w:drawing><wp:inline xmlns:wp=\"http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing\"><wp:extent cx=\"5486400\" cy=\"5486400\"/><wp:docPr id=\"1\" name=\"Tiger-ZiWei Chart\"/><a:graphic xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\"><a:graphicData uri=\"http://schemas.openxmlformats.org/drawingml/2006/picture\"><pic:pic xmlns:pic=\"http://schemas.openxmlformats.org/drawingml/2006/picture\"><pic:nvPicPr><pic:cNvPr id=\"0\" name=\"chart.png\"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" r:embed=\"rId2\"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"5486400\" cy=\"5486400\"/></a:xfrm><a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>")
        body.heading("本命十二宮", 2)
        body.table(listOf("宮位", "宮干支", "主星", "輔星", "命／身"), chart.palaces.map { p ->
            listOf(p.palace_name, p.palace_ganzhi.display, p.major_stars.joinToString("、") { it.name }.ifBlank { "—" }, p.auxiliary_stars.joinToString("、") { it.name }.ifBlank { "—" }, buildString { if (p.is_life_palace) append("【命】"); if (p.has_body_palace) append("【身】") }.ifBlank { "—" })
        })
        body.heading("生年四化", 2)
        body.table(listOf("四化", "星曜", "本命宮", "地支"), chart.birth_year_transformations.transformations.map { listOf(it.transformation, it.star_name, it.palace_name, it.earthly_branch) })
        interpretations["natal"]?.let { body.interpretation("本命 AI 解讀", it) }

        body.heading("完整大限", 2)
        body.paragraph("大限方向：${chart.major_luck.direction}；五行局起限：${chart.major_luck.bureau_number} 虛歲。")
        body.table(listOf("大限", "虛歲", "宮位", "地支", "宮干支", "大限四化"), chart.major_luck.periods.mapIndexed { index, p ->
            val changes = chart.major_luck.period_transformations[index].transformations.joinToString("、") { "${it.transformation_type}${it.star_name}（${it.natal_palace_name}）" }
            listOf(p.index.toString(), "${p.start_nominal_age}–${p.end_nominal_age}", p.palace_name, p.earthly_branch, p.palace_ganzhi.display, changes)
        })
        interpretations["major_luck"]?.let { body.interpretation("大限 AI 解讀", it) }

        flow?.let { result ->
            body.pageBreak(); body.heading("運限查詢", 1)
            val target = result.normalized_target
            body.paragraph("查詢模式：${if (result.query_mode == "solar") "國曆" else "農曆"}；原國曆日期：${target.original_solar_date ?: target.converted_solar_date ?: "年／月層級"}。")
            body.paragraph("農曆目標：${target.lunar_year} 年 ${if (target.is_leap_month) "閏" else ""}${target.lunar_month ?: "—"} 月 ${target.lunar_day ?: "—"} 日；有效月：${target.effective_month ?: "—"}。")
            val y = result.flow_year
            body.heading("流年 ${y.target_lunar_year}", 2)
            body.table(listOf("欄位", "內容"), listOf(listOf("干支", y.ganzhi.display), listOf("虛歲", y.nominal_age.toString()), listOf("流年命宮", y.flow_life_palace_branch)))
            body.paragraph(y.active_major_luck?.let { "目前大限：第 ${it.index} 大限 ${it.start_nominal_age}–${it.end_nominal_age} 虛歲，${it.palace_name} ${it.palace_ganzhi.display}。" } ?: if (y.before_first_major_luck) "尚未進入第一大限。" else "已超出支援的十二大限。")
            body.table(listOf("流年宮位", "地支", "本命宿宮", "本命宮干支"), y.palaces.map { listOf(it.flow_palace_name, it.earthly_branch, it.natal_palace_name, it.natal_palace_ganzhi.display) })
            body.transformTable("流年四化", y.transformations)
            interpretations["flow_year"]?.let { body.interpretation("流年 AI 解讀", it) }
            result.flow_month?.let { m ->
                body.heading("流月 ${if (m.is_leap_month) "閏" else ""}${m.lunar_month}", 2)
                body.table(listOf("欄位", "內容"), listOf(listOf("干支", m.month_ganzhi.display), listOf("流月命宮", m.flow_month_life_palace_branch), listOf("本命宿宮", m.natal_host_palace_name)))
                body.table(listOf("流月宮位", "地支", "本命宿宮", "本命宮干支"), m.palaces.map { listOf(it.flow_palace_name, it.earthly_branch, it.natal_palace_name, it.natal_palace_ganzhi.display) })
                body.transformTable("流月四化", m.transformations)
                interpretations["flow_month"]?.let { body.interpretation("流月 AI 解讀", it) }
            }
            result.flow_day?.let { d ->
                body.heading("流日 ${d.target_lunar_day}", 2)
                body.table(listOf("欄位", "內容"), listOf(listOf("干支", d.day_ganzhi.display), listOf("流日命宮", d.flow_day_life_palace_branch), listOf("本命宿宮", d.natal_host_palace_name)))
                body.table(listOf("流日宮位", "地支", "本命宿宮", "本命宮干支"), d.palaces.map { listOf(it.flow_palace_name, it.earthly_branch, it.natal_palace_name, it.natal_palace_ganzhi.display) })
                body.transformTable("流日四化", d.transformations)
                interpretations["flow_day"]?.let { body.interpretation("流日 AI 解讀", it) }
            }
        }
        body.heading("參考說明", 2)
        body.paragraph("本報告屬傳統紫微斗數觀點，供文化研究與自我反思參考，不代表科學結論，不應取代醫療、法律或財務專業建議。真太陽時、流時、移動星曜、小限與童限尚未實作。")
        val document = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>$body<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1000" w:right="1000" w:bottom="1000" w:left="1000"/></w:sectPr></w:body></w:document>"""
        return zip(document, chartPng)
    }

    private fun StringBuilder.transformTable(title: String, rows: List<*>) {
        heading(title, 3)
        val converted = rows.map { row ->
            when (row) {
                is LocatedTransformation -> listOf(row.transformation_type, row.star_name, row.natal_palace_name, row.earthly_branch)
                is FlowPeriodTransformation -> listOf(row.transformation_type, row.star_name, row.natal_palace_name, row.natal_branch)
                else -> emptyList()
            }
        }
        table(listOf("四化", "星曜", "本命宮", "地支"), converted)
    }

    private fun StringBuilder.interpretation(title: String, json: JsonObject) {
        heading(title, 2)
        json["model_display_name"]?.takeUnless { it.isJsonNull }?.let { paragraph("AI 模型：${it.asString}") }
        val ignored = setOf("model", "model_display_name", "reasoning_effort", "provided_by")
        fun walk(prefix: String, e: JsonElement) {
            when {
                e.isJsonPrimitive && e.asJsonPrimitive.isString -> paragraph(if (prefix.isBlank()) e.asString else "$prefix：${e.asString}")
                e.isJsonPrimitive -> paragraph("$prefix：${e.asString}")
                e.isJsonArray -> e.asJsonArray.forEach { walk(prefix, it) }
                e.isJsonObject -> e.asJsonObject.entrySet().filter { it.key !in ignored }.forEach { walk(label(it.key), it.value) }
            }
        }
        walk("", json)
    }

    private fun label(key: String) = mapOf(
        "overview" to "總覽", "analysis" to "分析", "summary" to "摘要", "palace_name" to "宮位", "earthly_branch" to "地支", "heavenly_stem" to "天干",
        "major_luck_index" to "大限", "start_nominal_age" to "起始虛歲", "end_nominal_age" to "終止虛歲", "target_year" to "流年", "nominal_age" to "虛歲",
        "lunar_year" to "農曆年", "lunar_month" to "農曆月", "lunar_day" to "農曆日", "is_leap_month" to "閏月", "status" to "狀態",
        "flow_life_palace_branch" to "流年命宮", "flow_month_life_palace_branch" to "流月命宮", "flow_day_life_palace_branch" to "流日命宮", "natal_host_palace" to "本命宿宮",
        "transformation_type" to "四化", "star_name" to "星曜", "natal_palace_name" to "本命宮位", "host_palace_analysis" to "大限所在宮分析", "flow_life_palace_analysis" to "流年命宮分析", "life_palace_analysis" to "命宮分析",
        "major_luck_context" to "大限背景", "flow_year_context" to "流年背景", "flow_month_context" to "流月背景", "personality" to "性格", "career" to "職涯", "work" to "工作", "finance" to "財務", "relationships" to "感情", "interpersonal" to "人際", "family" to "家庭", "family_and_interpersonal" to "家庭與人際", "strengths" to "優勢", "potential_challenges" to "可留意挑戰", "practical_focus" to "實際重點",
    )[key] ?: key
    private fun esc(value: String) = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;")
    private fun StringBuilder.heading(value: String, level: Int) { append("<w:p><w:pPr><w:pStyle w:val=\"Heading$level\"/></w:pPr><w:r><w:t>${esc(value)}</w:t></w:r></w:p>") }
    private fun StringBuilder.paragraph(value: String) { append("<w:p><w:r><w:t xml:space=\"preserve\">${esc(value)}</w:t></w:r></w:p>") }
    private fun StringBuilder.pageBreak() { append("<w:p><w:r><w:br w:type=\"page\"/></w:r></w:p>") }
    private fun StringBuilder.table(headers: List<String>, rows: List<List<String>>) {
        append("<w:tbl><w:tblPr><w:tblBorders><w:top w:val=\"single\" w:sz=\"4\"/><w:left w:val=\"single\" w:sz=\"4\"/><w:bottom w:val=\"single\" w:sz=\"4\"/><w:right w:val=\"single\" w:sz=\"4\"/><w:insideH w:val=\"single\" w:sz=\"4\"/><w:insideV w:val=\"single\" w:sz=\"4\"/></w:tblBorders></w:tblPr>")
        fun row(values: List<String>, bold: Boolean) { append("<w:tr>"); values.forEach { append("<w:tc><w:p><w:r>"); if (bold) append("<w:rPr><w:b/></w:rPr>"); append("<w:t>${esc(it)}</w:t></w:r></w:p></w:tc>") }; append("</w:tr>") }
        row(headers, true); rows.forEach { row(it, false) }; append("</w:tbl>")
    }

    private fun zip(document: String, png: ByteArray): ByteArray = ByteArrayOutputStream().use { out ->
        ZipOutputStream(out).use { zip ->
            fun entry(name: String, data: ByteArray) { zip.putNextEntry(ZipEntry(name)); zip.write(data); zip.closeEntry() }
            fun xml(name: String, value: String) = entry(name, value.toByteArray(Charsets.UTF_8))
            xml("[Content_Types].xml", """<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>""")
            xml("_rels/.rels", """<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>""")
            xml("word/document.xml", document)
            xml("word/_rels/document.xml.rels", """<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/chart.png"/></Relationships>""")
            xml("word/styles.xml", """<?xml version="1.0" encoding="UTF-8"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:rFonts w:eastAsia="Noto Sans CJK TC"/><w:sz w:val="22"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="32"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style></w:styles>""")
            entry("word/media/chart.png", png)
        }
        out.toByteArray()
    }
}
