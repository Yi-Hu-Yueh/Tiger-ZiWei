package com.tiger.ziwei

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import com.google.gson.JsonObject
import com.tiger.ziwei.core.ZiweiCore
import java.io.ByteArrayInputStream
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private lateinit var webView: WebView
    private val executor: ExecutorService = Executors.newFixedThreadPool(2)
    private val networkExecutor: ExecutorService = Executors.newFixedThreadPool(5)
    private val gson = ZiweiCore.gson
    private val allowedActions = setOf(
        "get_models", "calculate_chart", "calculate_flow_query", "generate_png", "generate_docx",
        "interpret_natal", "interpret_major_luck", "interpret_flow_year", "interpret_flow_month", "interpret_flow_day",
    )

    @SuppressLint("SetJavaScriptEnabled", "AddJavascriptInterface")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        title = "Tiger-ZiWei"
        WebView.setWebContentsDebuggingEnabled(false)
        webView = WebView(this).apply {
            importantForAutofill = android.view.View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = false
            settings.databaseEnabled = false
            settings.saveFormData = false
            settings.allowFileAccess = false
            settings.allowContentAccess = false
            settings.allowFileAccessFromFileURLs = false
            settings.allowUniversalAccessFromFileURLs = false
            settings.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW
            addJavascriptInterface(StrictBridge(), BRIDGE_NAME)
            webViewClient = PackagedAssetsClient()
        }
        setContentView(webView)
        webView.loadUrl("$LOCAL_ORIGIN/ziwei.html")
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() { if (webView.canGoBack()) webView.goBack() else super.onBackPressed() }

    override fun onDestroy() {
        webView.removeJavascriptInterface(BRIDGE_NAME)
        webView.stopLoading()
        webView.destroy()
        executor.shutdownNow()
        networkExecutor.shutdownNow()
        super.onDestroy()
    }

    private inner class StrictBridge {
        @JavascriptInterface
        fun request(requestId: String, action: String, jsonPayload: String) {
            if (action !in allowedActions || requestId.length !in 1..128 || jsonPayload.length > 2_000_000) {
                callback(requestId.take(128), false, error(400, "不支援的本機動作。"))
                return
            }
            val work = Runnable {
                try {
                    callback(requestId, true, StandaloneService(applicationContext).execute(action, jsonPayload))
                } catch (e: StandaloneException) {
                    callback(requestId, false, error(e.status, e.message))
                } catch (e: IllegalArgumentException) {
                    callback(requestId, false, error(422, e.message ?: "輸入資料無效。"))
                } catch (_: Exception) {
                    callback(requestId, false, error(500, "本機處理失敗，請重試。"))
                }
            }
            if (action.startsWith("interpret_")) networkExecutor.execute(work) else executor.execute(work)
        }
    }

    private fun error(status: Int, detail: String) = gson.toJson(JsonObject().apply {
        addProperty("status", status); addProperty("detail", detail)
    })

    private fun callback(requestId: String, success: Boolean, payload: String) = runOnUiThread {
        if (!isFinishing && !isDestroyed) {
            webView.evaluateJavascript(
                "window.TigerStandalone&&window.TigerStandalone.onResponse(${gson.toJson(requestId)},$success,${gson.toJson(payload)});",
                null,
            )
        }
    }

    private inner class PackagedAssetsClient : WebViewClient() {
        override fun shouldInterceptRequest(view: WebView?, request: WebResourceRequest?): WebResourceResponse? {
            val uri = request?.url ?: return forbidden()
            if (uri.scheme != "https" || uri.host != LOCAL_HOST || request.method != "GET") return forbidden()
            val raw = uri.path.orEmpty().removePrefix("/")
            val asset = if (raw.startsWith("static/")) raw.removePrefix("static/") else raw
            if (asset !in setOf("ziwei.html", "ziwei.css", "ziwei.js")) return forbidden()
            return try {
                val mime = when {
                    asset.endsWith(".html") -> "text/html"
                    asset.endsWith(".css") -> "text/css"
                    else -> "application/javascript"
                }
                WebResourceResponse(mime, "UTF-8", assets.open(asset))
            } catch (_: Exception) {
                forbidden()
            }
        }

        override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
            val uri = request?.url ?: return true
            if (uri.scheme == "https" && uri.host == LOCAL_HOST) return false
            if (uri.scheme == "https" || uri.scheme == "http") runCatching { startActivity(Intent(Intent.ACTION_VIEW, uri)) }
            return true
        }

        private fun forbidden() = WebResourceResponse(
            "text/plain", "UTF-8", 403, "Forbidden", emptyMap(), ByteArrayInputStream(ByteArray(0)),
        )
    }

    companion object {
        private const val BRIDGE_NAME = "TigerAndroid"
        private const val LOCAL_HOST = "appassets.androidplatform.net"
        private const val LOCAL_ORIGIN = "https://appassets.androidplatform.net"
    }
}
