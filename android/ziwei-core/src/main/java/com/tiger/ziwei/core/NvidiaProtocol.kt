package com.tiger.ziwei.core

import com.google.gson.JsonObject

object NvidiaProtocol {
    fun payload(modelId: String, scope: String, facts: JsonObject): JsonObject {
        val model = AiPolicy.model(modelId)
        return JsonObject().apply {
            addProperty("model", model.id)
            add("messages", AiPolicy.messages(scope, facts))
            addProperty("reasoning_effort", "low")
            addProperty("stream", false)
            addProperty("max_tokens", 3072)
            if (model.clear_thinking) add("chat_template_kwargs", JsonObject().apply { addProperty("clear_thinking", true) })
        }
    }

    fun visibleContent(root: JsonObject): String {
        val choice = root["choices"]?.asJsonArray?.takeIf { it.size() > 0 }?.get(0)?.asJsonObject
            ?: throw IllegalArgumentException("missing visible answer")
        require(choice["finish_reason"]?.takeUnless { it.isJsonNull }?.asString != "length") { "truncated response" }
        val content = choice["message"]?.asJsonObject?.get("content")
        require(content != null && content.isJsonPrimitive && content.asJsonPrimitive.isString && content.asString.isNotBlank()) { "missing visible answer" }
        return content.asString.trim()
    }
}
