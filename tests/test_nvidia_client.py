"""Mocked Phase 4A NVIDIA client tests; these never consume live quota."""

import asyncio
import json

import httpx
import pytest

import app.config as config_module
from app.config import (
    NVIDIA_API_URL,
    NVIDIA_CLEAR_THINKING,
    NVIDIA_MODEL,
    NVIDIA_REASONING_EFFORT,
    get_settings,
)
from app.llm.nvidia_client import NvidiaClient, NvidiaClientError, NvidiaErrorCode
from app.llm.interpreter import ZiweiInterpreter
from app.llm.major_luck_interpreter import MajorLuckInterpreter
from app.llm.flow_year_interpreter import FlowYearInterpreter


API_KEY = "test-key-that-is-not-a-real-secret"
MESSAGES = [{"role": "user", "content": "請回覆一個短句。"}]


def run_chat(transport: httpx.MockTransport, *, max_tokens: int = 64) -> str:
    return asyncio.run(
        NvidiaClient(api_key=API_KEY, transport=transport).chat(
            MESSAGES,
            max_tokens=max_tokens,
        )
    )


def response_json(
    content: object = "連線成功。",
    *,
    finish_reason: str = "stop",
    reasoning_content: str | None = None,
) -> dict[str, object]:
    message: dict[str, object] = {"role": "assistant", "content": content}
    if reasoning_content is not None:
        message["reasoning_content"] = reasoning_content
    return {"choices": [{"message": message, "finish_reason": finish_reason}]}


def test_fixed_official_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", API_KEY)
    settings = get_settings()
    assert NVIDIA_API_URL == "https://integrate.api.nvidia.com/v1/chat/completions"
    assert NVIDIA_MODEL == "z-ai/glm-5.3-flash"
    assert NVIDIA_REASONING_EFFORT == "low"
    assert NVIDIA_CLEAR_THINKING is True
    assert settings.nvidia_api_url == NVIDIA_API_URL
    assert settings.nvidia_model == NVIDIA_MODEL
    assert settings.nvidia_reasoning_effort == NVIDIA_REASONING_EFFORT


def test_project_dotenv_key_takes_precedence_over_process_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text('NVIDIA_API_KEY="project-key"\n', encoding="utf-8")
    monkeypatch.setattr(config_module, "PROJECT_ENV_PATH", env_path)
    monkeypatch.setenv("NVIDIA_API_KEY", "process-key")
    assert get_settings().nvidia_api_key == "project-key"


def test_process_environment_is_fallback_when_project_dotenv_has_no_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("OTHER_SETTING=value\n", encoding="utf-8")
    monkeypatch.setattr(config_module, "PROJECT_ENV_PATH", env_path)
    monkeypatch.setenv("NVIDIA_API_KEY", "process-key")
    assert get_settings().nvidia_api_key == "process-key"


def test_blank_project_dotenv_key_does_not_fall_back_to_process_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("NVIDIA_API_KEY=   \n", encoding="utf-8")
    monkeypatch.setattr(config_module, "PROJECT_ENV_PATH", env_path)
    monkeypatch.setenv("NVIDIA_API_KEY", "process-key")
    assert get_settings().nvidia_api_key is None


def test_exact_url_headers_and_minimal_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert str(request.url) == NVIDIA_API_URL
        assert request.headers["Authorization"] == f"Bearer {API_KEY}"
        assert request.headers["Content-Type"] == "application/json"
        assert request.headers["Accept"] == "application/json"
        assert payload == {
            "model": "z-ai/glm-5.3-flash",
            "messages": MESSAGES,
            "reasoning_effort": "low",
            "stream": False,
            "max_tokens": 64,
            "chat_template_kwargs": {"clear_thinking": True},
        }
        return httpx.Response(200, json=response_json(), request=request)

    assert run_chat(httpx.MockTransport(handler)) == "連線成功。"


@pytest.mark.parametrize(
    "interpreter_type",
    (ZiweiInterpreter, MajorLuckInterpreter, FlowYearInterpreter),
    ids=("natal", "major-luck", "flow-year"),
)
def test_all_interpreter_paths_use_shared_low_reasoning_client(interpreter_type) -> None:
    interpreter = interpreter_type()
    assert isinstance(interpreter._client, NvidiaClient)
    assert NVIDIA_MODEL == "z-ai/glm-5.3-flash"
    assert NVIDIA_REASONING_EFFORT == "low"
    assert NVIDIA_CLEAR_THINKING is True


def test_visible_content_is_parsed_and_reasoning_content_is_ignored() -> None:
    hidden = "This private reasoning must never reach the product output."

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=response_json("  可見答案。  ", reasoning_content=hidden),
            request=request,
        )

    answer = run_chat(httpx.MockTransport(handler))
    assert answer == "可見答案。"
    assert hidden not in answer


@pytest.mark.parametrize(
    ("status_code", "expected_code"),
    (
        (401, NvidiaErrorCode.AUTHENTICATION_ERROR),
        (403, NvidiaErrorCode.PERMISSION_ERROR),
        (402, NvidiaErrorCode.PAYMENT_OR_QUOTA_ERROR),
        (422, NvidiaErrorCode.REQUEST_VALIDATION_ERROR),
        (429, NvidiaErrorCode.RATE_LIMIT_ERROR),
        (500, NvidiaErrorCode.PROVIDER_ERROR),
        (503, NvidiaErrorCode.PROVIDER_ERROR),
    ),
)
def test_http_error_mapping(status_code: int, expected_code: NvidiaErrorCode) -> None:
    secret_from_provider = "provider-body-must-not-appear"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text=secret_from_provider, request=request)

    with pytest.raises(NvidiaClientError) as raised:
        run_chat(httpx.MockTransport(handler))
    assert raised.value.code is expected_code
    assert raised.value.status_code == status_code
    assert API_KEY not in str(raised.value)
    assert secret_from_provider not in str(raised.value)


def test_timeout_is_mapped_without_exposing_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("simulated timeout", request=request)

    with pytest.raises(NvidiaClientError) as raised:
        run_chat(httpx.MockTransport(handler))
    assert raised.value.code is NvidiaErrorCode.TIMEOUT
    assert API_KEY not in str(raised.value)


def test_other_http_transport_error_is_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated connection failure", request=request)

    with pytest.raises(NvidiaClientError) as raised:
        run_chat(httpx.MockTransport(handler))
    assert raised.value.code is NvidiaErrorCode.PROVIDER_ERROR


def test_malformed_json_is_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json", request=request)

    with pytest.raises(NvidiaClientError) as raised:
        run_chat(httpx.MockTransport(handler))
    assert raised.value.code is NvidiaErrorCode.PROVIDER_ERROR


@pytest.mark.parametrize(
    "payload",
    (
        {},
        {"choices": []},
        {"choices": [{}]},
        {"choices": [{"message": {}}]},
        response_json(""),
        response_json("   "),
        response_json(None),
    ),
)
def test_missing_or_empty_visible_answer_is_rejected(payload: dict[str, object]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload, request=request)

    with pytest.raises(NvidiaClientError) as raised:
        run_chat(httpx.MockTransport(handler))
    assert raised.value.code is NvidiaErrorCode.EMPTY_RESPONSE


def test_finish_reason_length_is_rejected_even_with_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=response_json("incomplete", finish_reason="length"),
            request=request,
        )

    with pytest.raises(NvidiaClientError) as raised:
        run_chat(httpx.MockTransport(handler))
    assert raised.value.code is NvidiaErrorCode.TRUNCATED_RESPONSE


def test_missing_api_key_is_rejected_before_transport() -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json=response_json(), request=request)

    with pytest.raises(NvidiaClientError) as raised:
        asyncio.run(NvidiaClient(api_key="", transport=httpx.MockTransport(handler)).chat(MESSAGES))
    assert raised.value.code is NvidiaErrorCode.MISSING_API_KEY
    assert called is False


def test_invalid_max_tokens_is_rejected_before_transport() -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json=response_json(), request=request)

    with pytest.raises(ValueError, match="max_tokens"):
        asyncio.run(
            NvidiaClient(api_key=API_KEY, transport=httpx.MockTransport(handler)).chat(
                MESSAGES,
                max_tokens=0,
            )
        )
    assert called is False
