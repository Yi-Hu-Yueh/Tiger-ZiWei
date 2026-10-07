package com.tiger.ziwei

import android.content.ContentValues
import android.content.Context
import android.provider.MediaStore
import android.util.Base64
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import com.tiger.ziwei.core.AiPolicy
import com.tiger.ziwei.core.BasicChartResult
import com.tiger.ziwei.core.BirthInput
import com.tiger.ziwei.core.DocxReport
import com.tiger.ziwei.core.FlowQueryInput
import com.tiger.ziwei.core.FlowQueryResult
import com.tiger.ziwei.core.InterpretationFacts
import com.tiger.ziwei.core.InputCodec
import com.tiger.ziwei.core.ChartRenderData
import com.tiger.ziwei.core.NvidiaProtocol
import com.tiger.ziwei.core.ZiweiCore
import java.io.IOException
import javax.net.ssl.HttpsURLConnection
import java.net.SocketTimeoutException
import java.net.URL

class StandaloneService(private val context: Context? = null) {
    private val gson = ZiweiCore.gson

    fun execute(action: String, envelopeJson: String): String {
        val envelope = JsonParser.parseString(envelopeJson).asJsonObject
        val body = envelope["body"]?.takeUnless { it.isJsonNull }?.asString.orEmpty()
        val headers = envelope["headers"]?.takeIf { it.isJsonObject }?.asJsonObject ?: JsonObject()
        return when (action) {
            "get_models" -> gson.toJson(AiPolicy.models.map { mapOf("id" to it.id, "display_name" to it.display_name, "default" to it.default) })
            "calculate_chart" -> gson.toJson(chart(body))
            "calculate_flow_query" -> {
                val request = objectBody(body)
                val c = chart(request["birth_input"].toString())
                gson.toJson(ZiweiCore.calculateFlowQuery(c, InputCodec.query(request["query"].asJsonObject)))
            }
            "generate_png" -> {
                val c = chart(body)
                val filename = ChartRenderData.filename(c)
                val bytes = ChartRenderer.png(c)
                if (envelope["saveToDownloads"]?.asBoolean == true) {
                    saveDownload(filename, "image/png", bytes)
                    gson.toJson(mapOf("saved" to true, "message" to "PNG 命盤已儲存至 Downloads"))
                } else gson.toJson(JsonObject().apply {
                    addProperty("_binary_base64", Base64.encodeToString(bytes, Base64.NO_WRAP))
                    addProperty("_mime", "image/png"); addProperty("_filename", filename)
                })
            }
            "generate_docx" -> generateDocx(body)
            "interpret_natal", "interpret_major_luck", "interpret_flow_year", "interpret_flow_month", "interpret_flow_day" -> interpret(action, body, headers)
            else -> throw IllegalArgumentException("不支援的本機動作。")
        }
    }

    private fun chart(json: String): BasicChartResult = ZiweiCore.calculateChart(InputCodec.birth(json))
    private fun objectBody(json: String): JsonObject = JsonParser.parseString(json).asJsonObject

    private fun interpretationContext(action: String, body: String): Pair<String, JsonObject> {
        if (action == "interpret_natal") {
            val c = chart(body); return "natal" to InterpretationFacts.natal(c)
        }
        val request = objectBody(body)
        val c = chart(request["birth_input"].toString())
        return when (action) {
            "interpret_major_luck" -> "major_luck" to InterpretationFacts.majorLuck(c, request["major_luck_index"].asInt)
            "interpret_flow_year" -> {
                val flow = ZiweiCore.flowYear(c, request["target_year"].asInt)
                "flow_year" to InterpretationFacts.flowYear(c, flow)
            }
            "interpret_flow_month", "interpret_flow_day" -> {
                val query = ZiweiCore.calculateFlowQuery(c, InputCodec.query(request["query"].asJsonObject))
                val month = query.flow_month ?: throw IllegalArgumentException("查詢未包含流月。")
                if (action == "interpret_flow_month") "flow_month" to InterpretationFacts.flowMonth(c, query.flow_year, month)
                else "flow_day" to InterpretationFacts.flowDay(c, query.flow_year, month, query.flow_day ?: throw IllegalArgumentException("查詢未包含流日。"))
            }
            else -> throw IllegalArgumentException("不支援的解讀類型。")
        }
    }

    private fun interpret(action: String, body: String, headers: JsonObject): String {
        val key = headers["X-Tiger-NVIDIA-API-Key"]?.asString?.trim().orEmpty()
        if (key.isBlank()) throw StandaloneException(401, "請輸入 NVIDIA API KEY。")
        val model = AiPolicy.model(headers["X-Tiger-NVIDIA-Model"]?.asString ?: AiPolicy.models.first { it.default }.id)
        val (scope, facts) = interpretationContext(action, body)
        val payload = NvidiaProtocol.payload(model.id, scope, facts)
        val raw = postNvidia(key, payload)
        val parsed = try {
            AiPolicy.parseProviderJson(raw).also { AiPolicy.validate(scope, facts, it) }
        } catch (_: Exception) {
            throw StandaloneException(502, "解盤回應格式驗證失敗。")
        }
        parsed.addProperty("provider", "NVIDIA"); parsed.addProperty("model", model.id); parsed.addProperty("model_display_name", model.display_name)
        return gson.toJson(parsed)
    }

    private fun postNvidia(apiKey: String, payload: JsonObject): String {
        var connection: HttpsURLConnection? = null
        try {
            connection = URL(AiPolicy.ENDPOINT).openConnection() as HttpsURLConnection
            connection.requestMethod = "POST"; connection.connectTimeout = 30_000; connection.readTimeout = 180_000
            connection.doOutput = true; connection.instanceFollowRedirects = false
            connection.setRequestProperty("Authorization", "Bearer $apiKey")
            connection.setRequestProperty("Content-Type", "application/json"); connection.setRequestProperty("Accept", "application/json")
            connection.outputStream.use { it.write(payload.toString().toByteArray(Charsets.UTF_8)) }
            val status = connection.responseCode
            if (status !in 200..299) throw StandaloneException(status, when (status) {
                401 -> "NVIDIA API KEY 驗證失敗。"; 403 -> "NVIDIA 拒絕此模型的存取權限。"; 429 -> "NVIDIA 請求過於頻繁，請稍後再試。"; else -> "NVIDIA 解讀請求失敗。"
            })
            val root = JsonParser.parseReader(connection.inputStream.reader(Charsets.UTF_8)).asJsonObject
            return try { NvidiaProtocol.visibleContent(root) } catch (_: Exception) { throw StandaloneException(502, "NVIDIA 未回傳完整可用解讀。") }
        } catch (_: SocketTimeoutException) {
            throw StandaloneException(504, "無法連線 NVIDIA，請檢查網路。")
        } catch (e: StandaloneException) {
            throw e
        } catch (_: IOException) {
            throw StandaloneException(503, "無法連線 NVIDIA，請檢查網路。")
        } finally { connection?.disconnect() }
    }

    private fun generateDocx(body: String): String {
        val request = objectBody(body); val c = chart(request["birth_input"].toString())
        val flow: FlowQueryResult? = request["flow_query"]?.takeUnless { it.isJsonNull }?.let { ZiweiCore.calculateFlowQuery(c, InputCodec.query(it.asJsonObject)) }
        val interpretations = linkedMapOf<String, JsonObject>()
        mapOf("natal" to "interpretation", "major_luck" to "major_luck_report", "flow_year" to "flow_year_interpretation", "flow_month" to "flow_month_interpretation", "flow_day" to "flow_day_interpretation").forEach { (scope, key) ->
            request[key]?.takeUnless { it.isJsonNull }?.asJsonObject?.let { value -> interpretations[scope] = if (key == "major_luck_report") value["interpretation"].asJsonObject else value }
        }
        interpretations.forEach { (scope, value) ->
            val facts = when (scope) {
                "natal" -> InterpretationFacts.natal(c)
                "major_luck" -> InterpretationFacts.majorLuck(c, request["major_luck_report"].asJsonObject["major_luck_index"].asInt)
                "flow_year" -> InterpretationFacts.flowYear(c, requireNotNull(flow).flow_year)
                "flow_month" -> InterpretationFacts.flowMonth(c, requireNotNull(flow).flow_year, requireNotNull(flow.flow_month))
                "flow_day" -> InterpretationFacts.flowDay(c, requireNotNull(flow).flow_year, requireNotNull(flow.flow_month), requireNotNull(flow.flow_day))
                else -> throw IllegalArgumentException("unknown report scope")
            }
            AiPolicy.validate(scope, facts, value)
        }
        val filename = DocxReport.filename(c, flow)
        val bytes = DocxReport.generate(c, ChartRenderer.png(c), flow, interpretations)
        saveDownload(filename, DocxReport.MIME, bytes)
        return gson.toJson(JsonObject().apply { addProperty("saved", true); addProperty("filename", filename); addProperty("message", "Word 報告已儲存至 Downloads") })
    }

    private fun saveDownload(filename: String, mime: String, bytes: ByteArray) {
        val resolver = requireNotNull(context).contentResolver
        val values = ContentValues().apply { put(MediaStore.Downloads.DISPLAY_NAME, filename); put(MediaStore.Downloads.MIME_TYPE, mime); put(MediaStore.Downloads.IS_PENDING, 1) }
        val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values) ?: throw StandaloneException(500, "檔案儲存失敗。")
        try {
            resolver.openOutputStream(uri)?.use { it.write(bytes) } ?: throw StandaloneException(500, "檔案儲存失敗。")
            values.clear(); values.put(MediaStore.Downloads.IS_PENDING, 0); resolver.update(uri, values, null, null)
        } catch (e: Exception) { resolver.delete(uri, null, null); throw e }
    }
}

class StandaloneException(val status: Int, override val message: String) : RuntimeException(message)
