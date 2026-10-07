package com.tiger.ziwei

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import com.tiger.ziwei.core.BasicChartResult
import com.tiger.ziwei.core.ChartRenderData
import java.io.ByteArrayOutputStream

/** Android Canvas port of the approved 24px margin / 400px cell renderer. */
object ChartRenderer {
    private val gridPositions = mapOf(
        "巳" to (0 to 0), "午" to (1 to 0), "未" to (2 to 0), "申" to (3 to 0),
        "辰" to (0 to 1), "酉" to (3 to 1), "卯" to (0 to 2), "戌" to (3 to 2),
        "寅" to (0 to 3), "丑" to (1 to 3), "子" to (2 to 3), "亥" to (3 to 3),
    )
    private fun paint(size: Float, color: String, bold: Boolean = false) = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        textSize = size; this.color = Color.parseColor(color)
        typeface = Typeface.create("sans-serif", if (bold) Typeface.BOLD else Typeface.NORMAL)
    }
    private fun text(canvas: Canvas, value: String, x: Float, y: Float, paint: Paint, maxWidth: Float = 10000f) {
        val fitted = Paint(paint)
        while (fitted.measureText(value) > maxWidth && fitted.textSize > 12f) fitted.textSize -= 1f
        canvas.drawText(value, x, y, fitted)
    }
    private fun lines(items: List<String>, paint: Paint, width: Float): List<String> {
        if (items.isEmpty()) return listOf("—")
        val result = mutableListOf<String>()
        var line = ""
        items.forEach { item ->
            val joined = if (line.isEmpty()) item else "${line}、$item"
            if (line.isNotEmpty() && paint.measureText(joined) > width) { result += line; line = item } else line = joined
        }
        if (line.isNotEmpty()) result += line
        return result
    }

    fun png(chart: BasicChartResult): ByteArray {
        val data = ChartRenderData.from(chart)
        val bitmap = Bitmap.createBitmap(data.width, data.height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        canvas.drawColor(Color.parseColor("#eee4d2"))
        val border = paint(1f, "#7d342d").apply { style = Paint.Style.STROKE; strokeWidth = 3f }
        val fill = paint(1f, "#fffdf7")
        val heading = paint(34f, "#6f211d", true)
        val marker = paint(24f, "#a33b2f", true)
        val luck = paint(22f, "#7d342d", true)
        val label = paint(19f, "#8b776b")
        val major = paint(30f, "#24201e", true)
        val auxiliary = paint(24f, "#514b47")
        data.cells.forEach { cell ->
            val (gx, gy) = gridPositions.getValue(cell.branch)
            val left = 24f + gx * 400f; val top = 24f + gy * 400f
            val box = RectF(left, top, left + 400f, top + 400f)
            canvas.drawRoundRect(box, 12f, 12f, fill); canvas.drawRoundRect(box, 12f, 12f, border)
            text(canvas, cell.palace, left + 16, top + 45, heading)
            text(canvas, cell.ganzhi, left + 384 - heading.measureText(cell.ganzhi), top + 45, heading)
            text(canvas, cell.markers.joinToString(" "), left + 16, top + 84, marker)
            val age = cell.majorLuckAge + "歲"
            text(canvas, age, left + 384 - luck.measureText(age), top + 84, luck)
            var y = top + 126f
            text(canvas, "主星", left + 16, y, label); y += 33f
            lines(cell.majorStars, major, 368f).forEach { text(canvas, it, left + 16, y, major, 368f); y += 38f }
            y += 13f
            text(canvas, "輔星", left + 16, y, label); y += 29f
            lines(cell.auxiliaryStars, auxiliary, 368f).forEach { text(canvas, it, left + 16, y, auxiliary, 368f); y += 32f }
        }
        val x0 = 424f; val y0 = 424f
        val center = RectF(x0, y0, 1224f, 1224f)
        canvas.drawRoundRect(center, 14f, 14f, paint(1f, "#f8f0df"))
        canvas.drawRoundRect(center, 14f, 14f, border)
        val title = paint(42f, "#6f211d", true)
        val titleText = "Tiger-ZiWei 紫微命盤"
        text(canvas, titleText, 824f - title.measureText(titleText) / 2, y0 + 66f, title)
        val divider = paint(1f, "#bd9b61").apply { strokeWidth = 2f }
        canvas.drawLine(x0 + 28, y0 + 88, 1196f, y0 + 88, divider)
        val normal = paint(24f, "#28211f")
        val subhead = paint(26f, "#6f211d", true)
        val birth = chart.birth_data; val lunar = chart.calendar.lunar_date
        fun group(titleValue: String, rows: List<Pair<String, String>>, x: Float, y: Float): Float {
            text(canvas, titleValue, x, y + 26, subhead)
            var baseline = y + 63
            rows.forEach { (name, value) -> text(canvas, "$name：$value", x, baseline, normal, 345f); baseline += 36f }
            return baseline
        }
        group("基本資料", listOf(
            "姓名" to (birth.name ?: "未填寫"), "性別" to if (birth.gender == "female") "女" else "男",
            "西元日期" to chart.calendar.solar_date, "出生時間" to "%02d:%02d".format(java.util.Locale.ROOT, birth.birth_hour, birth.birth_minute),
            "出生地" to birth.birthplace,
        ), x0 + 30, y0 + 108)
        group("曆法", listOf(
            "農曆日期" to "${lunar.year} 年 ${if (lunar.is_leap_month) "閏" else ""}${lunar.month} 月 ${lunar.day} 日",
            "年干支" to chart.calendar.year_ganzhi.display, "月干支" to chart.calendar.month_ganzhi.display,
            "日干支" to chart.calendar.day_ganzhi.display, "時干支" to chart.calendar.hour_ganzhi.display,
        ), x0 + 414, y0 + 108)
        canvas.drawLine(x0 + 28, y0 + 338, 1196f, y0 + 338, divider)
        val next = group("命盤", listOf(
            "命宮" to chart.life_palace_branch, "身宮" to chart.body_palace_branch,
            "身宮宿宮" to chart.body_palace_name, "五行局" to chart.five_elements_bureau.bureau_name,
        ), x0 + 30, y0 + 354)
        group("月規則", listOf(
            "實際農曆月" to lunar.month.toString(), "閏月" to if (lunar.is_leap_month) "是" else "否",
            "有效本命月" to chart.palace_layout.effective_lunar_month.toString(),
        ), x0 + 30, next + 10)
        text(canvas, "生年四化", x0 + 414, y0 + 380, subhead)
        var transformationY = y0 + 422f
        chart.birth_year_transformations.transformations.forEach { item ->
            text(canvas, "${item.transformation}　${item.star_name}", x0 + 414, transformationY, normal)
            text(canvas, "${item.earthly_branch}・${item.palace_name}", x0 + 614, transformationY, paint(20f, "#765f54"), 165f)
            transformationY += 43f
        }
        val footer = "本圖僅呈現已驗證排盤資料｜不含解讀｜LLM 不參與排盤"
        val footerPaint = paint(18f, "#756b63")
        text(canvas, footer, 824f - footerPaint.measureText(footer) / 2, 1194f, footerPaint)
        return ByteArrayOutputStream().use { out -> bitmap.compress(Bitmap.CompressFormat.PNG, 100, out); bitmap.recycle(); out.toByteArray() }
    }
}

