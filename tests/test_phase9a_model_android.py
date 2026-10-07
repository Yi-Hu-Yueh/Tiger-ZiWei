"""Phase 9A model selection, transient credentials, and Android-client gates."""

import asyncio
import json
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.api.llm_request import resolve_llm_request_selection
from app.llm.model_registry import default_model, enabled_models, get_model_config
from app.llm.nvidia_client import NvidiaClient
from app.main import app


ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def test_safe_model_registry_endpoint_and_default() -> None:
    response = client.get("/api/llm/models")
    assert response.status_code == 200
    assert response.json() == [
        {"id": "z-ai/glm-5.3-flash", "display_name": "GLM-5.3-Flash", "default": True},
        {"id": "openai/gpt-oss-20b", "display_name": "GPT-OSS-20B", "default": False},
    ]
    assert default_model().id == "z-ai/glm-5.3-flash"
    assert all(model.reasoning_effort == "low" for model in enabled_models())
    assert "api_key" not in response.text.lower()
    assert "nvapi-" not in response.text.lower()


def test_model_registry_rejects_unlisted_model() -> None:
    try:
        get_model_config("untrusted/model")
    except ValueError as exc:
        assert str(exc) == "unsupported NVIDIA model"
    else:
        raise AssertionError("unlisted model was accepted")


def test_request_key_precedence_is_request_scoped() -> None:
    selection = resolve_llm_request_selection(
        api_key="  transient-browser-key  ", model_id="openai/gpt-oss-20b"
    )
    configured = selection.client(timeout=1)
    assert configured._api_key == "transient-browser-key"
    assert configured._model.id == "openai/gpt-oss-20b"


def test_each_selectable_model_uses_exact_supported_payload() -> None:
    expected_by_model = {
        "z-ai/glm-5.3-flash": {"chat_template_kwargs": {"clear_thinking": True}},
        "openai/gpt-oss-20b": {},
    }
    for model_id, model_specific in expected_by_model.items():
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen.update(json.loads(request.content))
            assert request.headers["Authorization"] == "Bearer transient-browser-key"
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "完成"}, "finish_reason": "stop"}]},
                request=request,
            )

        result = asyncio.run(NvidiaClient(
            api_key="transient-browser-key",
            model_id=model_id,
            transport=httpx.MockTransport(handler),
        ).chat([{"role": "user", "content": "test"}], max_tokens=10))
        assert result == "完成"
        assert seen["model"] == model_id
        assert seen["reasoning_effort"] == "low"
        if model_specific:
            assert seen["chat_template_kwargs"] == {"clear_thinking": True}
        else:
            assert "chat_template_kwargs" not in seen


def test_all_five_interpretation_scopes_use_shared_request_selection() -> None:
    files = (
        ROOT / "app/api/chart.py",
        ROOT / "app/api/major_luck_interpretation.py",
        ROOT / "app/api/flow_year_interpretation.py",
        ROOT / "app/api/flow_period_interpretation.py",
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
    for endpoint in (
        '"/api/interpret"',
        '"/api/major-luck/interpret"',
        '"/api/flow-year/interpret"',
        '"/api/flow-month/interpret"',
        '"/api/flow-day/interpret"',
    ):
        assert endpoint in combined
    assert combined.count("Depends(resolve_llm_request_selection)") == 5
    assert combined.count("attach_llm_metadata(") == 5


def test_api_key_ui_is_masked_transient_and_interpretation_only() -> None:
    html = (ROOT / "app/static/ziwei.html").read_text(encoding="utf-8")
    javascript = (ROOT / "app/static/ziwei.js").read_text(encoding="utf-8")
    assert "AI 設定" in html
    assert 'id="ai-model-select"' in html
    key_start = html.index('id="nvidia-api-key"')
    key_tag = html[html.rfind("<input", 0, key_start):html.index(">", key_start) + 1]
    assert 'type="password"' in key_tag
    assert "value=" not in key_tag
    assert 'autocomplete="off"' in key_tag
    for storage_api in ("localStorage", "sessionStorage", "indexedDB", "document.cookie"):
        assert storage_api not in javascript
    assert "X-Tiger-NVIDIA-API-Key" in javascript
    assert "X-Tiger-NVIDIA-Model" in javascript
    deterministic_blocks = (
        javascript[javascript.index('fetch("/api/chart"'):],
        javascript[javascript.index('fetch("/api/chart/png"'):javascript.index('fetch("/api/major-luck/interpret"')],
        javascript[javascript.index('fetch("/api/report/docx"'):javascript.index('fetch("/api/chart"')],
        javascript[javascript.index('fetch("/api/flow-query"'):javascript.index("async function fetchStructuredFlowInterpretation")],
    )
    assert all("interpretationRequestHeaders()" not in block for block in deterministic_blocks)


def test_model_change_clears_ai_only_without_network() -> None:
    javascript = (ROOT / "app/static/ziwei.js").read_text(encoding="utf-8")
    block = javascript[
        javascript.index("function invalidateAiInterpretationsForModelChange"):
        javascript.index("function flowYearErrorMessage")
    ]
    for clear_call in (
        "clearInterpretation()",
        "clearMajorLuckInterpretation()",
        "clearFlowYearInterpretation()",
        "clearFlowMonthInterpretation()",
        "clearFlowDayInterpretation()",
    ):
        assert clear_call in block
    assert "fetch(" not in block
    assert "invalidateFlowYear()" not in block
    assert "currentChart = null" not in block
    assert 'aiModelSelect.addEventListener("change", invalidateAiInterpretationsForModelChange)' in javascript


def test_android_standalone_is_origin_restricted_and_uses_local_exports() -> None:
    android = ROOT / "android"
    gradle = (android / "app/build.gradle.kts").read_text(encoding="utf-8")
    manifest = (android / "app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
    activity = (android / "app/src/main/java/com/tiger/ziwei/MainActivity.kt").read_text(encoding="utf-8")
    service = (android / "app/src/main/java/com/tiger/ziwei/StandaloneService.kt").read_text(encoding="utf-8")
    assert 'applicationId = "com.tiger.ziwei"' in gradle
    assert "minSdk = 29" in gradle
    assert "android.permission.INTERNET" in manifest
    assert "settings.javaScriptEnabled = true" in activity
    assert "settings.allowFileAccess = false" in activity
    assert "settings.allowUniversalAccessFromFileURLs = false" in activity
    assert 'LOCAL_HOST = "appassets.androidplatform.net"' in activity
    assert "uri.host != LOCAL_HOST" in activity
    assert "Intent.ACTION_VIEW" in activity
    assert "fun request(requestId: String, action: String, jsonPayload: String)" in activity
    assert "executor.execute" in activity
    assert "MediaStore.Downloads" in service
    assert "DocxReport.MIME" in service
    assert "NVIDIA_API_KEY" not in activity
    assert "nvidia_api_key" not in activity.lower()
    assert "putString(" not in activity
    assert "SharedPreferences" not in activity
    assert "10.0.2.2" not in activity
    assert "/health" not in activity
    assert 'manifestPlaceholders["usesCleartextTraffic"] = "false"' in gradle
    assert "Runtime.getRuntime" not in activity
    assert "ProcessBuilder" not in activity
    assert "openInputStream" not in activity


def test_android_bridge_uses_fixed_async_action_mapping() -> None:
    javascript = (ROOT / "app/static/ziwei.js").read_text(encoding="utf-8")
    assert "TigerAndroid.saveBase64File" not in javascript
    assert "window.TigerAndroid.request(requestId, action" in javascript
    assert "nativeActions.get" in javascript
    assert "pending.delete(requestId)" in javascript
    assert "TigerAndroid.fetch" not in javascript
    assert "TigerAndroid.read" not in javascript

