package com.tiger.ziwei.core

import com.google.gson.JsonElement
import com.google.gson.JsonObject

/** Small validator for the JSON-schema vocabulary emitted by Tiger Pydantic models. */
object ResponseSchema {
    fun validate(scope: String, value: JsonObject) {
        val root = AcceptedAiContracts.schemas[scope].asJsonObject
        validateNode(root, value, root, "response")
        applyDefaults(root, value, root)
        val metadata = listOf("provider", "model", "model_display_name").map { value[it]?.takeUnless { it.isJsonNull } }
        require(metadata.all { it == null } || metadata.all { it != null }) { "incomplete provider metadata" }
    }

    private fun applyDefaults(schema: JsonObject, value: JsonElement, root: JsonObject) {
        schema["\$ref"]?.let { reference ->
            var target: JsonElement = root
            reference.asString.removePrefix("#/").split('/').forEach { target = target.asJsonObject[it] }
            applyDefaults(target.asJsonObject, value, root)
            return
        }
        schema["anyOf"]?.let { choices ->
            choices.asJsonArray.firstOrNull { runCatching { validateNode(it.asJsonObject, value, root, "response") }.isSuccess }
                ?.let { applyDefaults(it.asJsonObject, value, root) }
            return
        }
        if (value.isJsonObject) {
            schema["properties"]?.asJsonObject?.entrySet()?.forEach { (key, property) ->
                val obj = value.asJsonObject; val p = property.asJsonObject
                if (!obj.has(key) && p.has("default")) obj.add(key, p["default"].deepCopy())
                obj[key]?.let { applyDefaults(p, it, root) }
            }
        } else if (value.isJsonArray) {
            schema["items"]?.let { item -> value.asJsonArray.forEach { applyDefaults(item.asJsonObject, it, root) } }
        }
    }

    private fun validateNode(schema: JsonObject, value: JsonElement, root: JsonObject, path: String) {
        schema["\$ref"]?.let { reference ->
            var target: JsonElement = root
            reference.asString.removePrefix("#/").split('/').forEach { target = target.asJsonObject[it] }
            validateNode(target.asJsonObject, value, root, path)
            return
        }
        schema["anyOf"]?.let { alternatives ->
            require(alternatives.asJsonArray.any { runCatching { validateNode(it.asJsonObject, value, root, path) }.isSuccess }) { "$path has wrong type" }
            return
        }
        schema["const"]?.let { require(value == it) { "$path has invalid constant" } }
        schema["enum"]?.let { require(it.asJsonArray.any { option -> option == value }) { "$path has invalid enum" } }
        when (schema["type"]?.asString) {
            "null" -> require(value.isJsonNull) { "$path must be null" }
            "object" -> {
                require(value.isJsonObject) { "$path must be an object" }
                val obj = value.asJsonObject
                schema["required"]?.asJsonArray?.forEach { require(obj.has(it.asString)) { "$path missing ${it.asString}" } }
                val properties = schema["properties"]?.asJsonObject ?: JsonObject()
                if (schema["additionalProperties"]?.let { it.isJsonPrimitive && it.asJsonPrimitive.isBoolean && !it.asBoolean } == true) {
                    require(obj.keySet().all { properties.has(it) }) { "$path has unknown fields" }
                }
                obj.entrySet().forEach { (key, item) -> properties[key]?.let { validateNode(it.asJsonObject, item, root, "$path.$key") } }
            }
            "array" -> {
                require(value.isJsonArray) { "$path must be an array" }
                val array = value.asJsonArray
                schema["minItems"]?.let { require(array.size() >= it.asInt) { "$path too short" } }
                schema["maxItems"]?.let { require(array.size() <= it.asInt) { "$path too long" } }
                schema["items"]?.let { itemSchema -> array.forEachIndexed { index, item -> validateNode(itemSchema.asJsonObject, item, root, "$path[$index]") } }
            }
            "string" -> {
                require(value.isJsonPrimitive && value.asJsonPrimitive.isString) { "$path must be text" }
                val text = value.asString.trim()
                schema["minLength"]?.let { require(text.length >= it.asInt) { "$path empty text" } }
                schema["maxLength"]?.let { require(text.length <= it.asInt) { "$path text too long" } }
                schema["pattern"]?.let { require(Regex(it.asString).containsMatchIn(text)) { "$path invalid text" } }
            }
            "integer", "number" -> {
                require(value.isJsonPrimitive && value.asJsonPrimitive.isNumber) { "$path must be numeric" }
                val number = value.asBigDecimal
                if (schema["type"].asString == "integer") require(number.stripTrailingZeros().scale() <= 0) { "$path must be an integer" }
                schema["minimum"]?.let { require(number >= it.asBigDecimal) { "$path below minimum" } }
                schema["maximum"]?.let { require(number <= it.asBigDecimal) { "$path above maximum" } }
            }
            "boolean" -> require(value.isJsonPrimitive && value.asJsonPrimitive.isBoolean) { "$path must be boolean" }
        }
    }
}
