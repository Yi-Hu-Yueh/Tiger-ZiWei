package com.tiger.ziwei.core

import com.google.gson.JsonParser
import org.junit.Assert.*
import org.junit.Test

class NvidiaProtocolTest {
    @Test fun allowlistedModelsUseOnlySupportedProviderOptions() {
        val facts = JsonParser.parseString(javaClass.classLoader!!.getResourceAsStream("interpretation_facts_natal.json")!!.bufferedReader().use { it.readText() }).asJsonObject
        AiPolicy.models.forEach { model ->
            val payload = NvidiaProtocol.payload(model.id, "natal", facts)
            assertEquals("low", payload["reasoning_effort"].asString)
            assertEquals(3072, payload["max_tokens"].asInt)
            assertFalse(payload["stream"].asBoolean)
            assertEquals(model.clear_thinking, payload.has("chat_template_kwargs"))
            assertEquals(AcceptedAiContracts.systemPrompts.getValue("natal"), payload["messages"].asJsonArray[0].asJsonObject["content"].asString)
        }
        assertThrows(IllegalArgumentException::class.java) { AiPolicy.model("untrusted/model") }
    }

    @Test fun onlyVisibleContentIsReturnedAndTruncationIsRejected() {
        val response = JsonParser.parseString("""{"choices":[{"message":{"content":"完成","reasoning_content":"private reasoning"},"finish_reason":"stop"}]}""").asJsonObject
        assertEquals("完成", NvidiaProtocol.visibleContent(response))
        response["choices"].asJsonArray[0].asJsonObject.addProperty("finish_reason", "length")
        assertThrows(IllegalArgumentException::class.java) { NvidiaProtocol.visibleContent(response) }
    }
}
