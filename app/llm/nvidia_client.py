"""Minimal secret-safe client for allowlisted NVIDIA-hosted chat models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence

import httpx

from app.config import NVIDIA_API_URL, get_settings
from app.llm.model_registry import LLMModelConfig, get_model_config


DEFAULT_MAX_TOKENS = 256
DEFAULT_TIMEOUT_SECONDS = 120.0


class NvidiaErrorCode(str, Enum):
    MISSING_API_KEY = "MISSING_API_KEY"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    PERMISSION_ERROR = "PERMISSION_ERROR"
    PAYMENT_OR_QUOTA_ERROR = "PAYMENT_OR_QUOTA_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    REQUEST_VALIDATION_ERROR = "REQUEST_VALIDATION_ERROR"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    TIMEOUT = "TIMEOUT"
    EMPTY_RESPONSE = "EMPTY_RESPONSE"
    TRUNCATED_RESPONSE = "TRUNCATED_RESPONSE"


class NvidiaClientError(RuntimeError):
    """A concise provider error that never stores request secrets."""

    def __init__(
        self,
        code: NvidiaErrorCode,
        message: str,
        *,
        status_code: int | None = None,
    ) -> None:
        super().__init__(f"{code.value}: {message}")
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class NvidiaChatResult:
    """Non-sensitive receipt for a successfully parsed visible answer."""

    content: str
    finish_reason: str | None
    http_status: int


def _http_error(status_code: int) -> NvidiaClientError:
    mapping = {
        401: (NvidiaErrorCode.AUTHENTICATION_ERROR, "NVIDIA rejected the API credentials."),
        403: (NvidiaErrorCode.PERMISSION_ERROR, "NVIDIA denied access to the requested model."),
        402: (NvidiaErrorCode.PAYMENT_OR_QUOTA_ERROR, "NVIDIA reported a payment or quota problem."),
        422: (NvidiaErrorCode.REQUEST_VALIDATION_ERROR, "NVIDIA rejected the request payload."),
        429: (NvidiaErrorCode.RATE_LIMIT_ERROR, "NVIDIA rate-limited the request."),
    }
    code, message = mapping.get(
        status_code,
        (NvidiaErrorCode.PROVIDER_ERROR, "NVIDIA returned an unsuccessful response."),
    )
    return NvidiaClientError(code, message, status_code=status_code)


class NvidiaClient:
    """Call one allowlisted NVIDIA model without a provider abstraction layer."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model_id: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        configured_key = api_key if api_key is not None else get_settings().nvidia_api_key
        self._api_key = configured_key.strip() if configured_key else None
        self._model: LLMModelConfig = get_model_config(model_id)
        self._timeout = timeout
        self._transport = transport

    async def chat(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> str:
        """Return only choices[0].message.content from a non-streaming call."""

        return (await self.chat_result(messages, max_tokens=max_tokens)).content

    async def chat_result(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> NvidiaChatResult:
        """Return visible content plus non-sensitive smoke-test diagnostics."""

        if not self._api_key or not self._api_key.strip():
            raise NvidiaClientError(
                NvidiaErrorCode.MISSING_API_KEY,
                "NVIDIA_API_KEY is not configured.",
            )
        if max_tokens < 1:
            raise ValueError("max_tokens must be at least 1")

        payload = {
            "model": self._model.id,
            "messages": [dict(message) for message in messages],
            "reasoning_effort": self._model.reasoning_effort,
            "stream": False,
            "max_tokens": max_tokens,
        }
        if self._model.supports_clear_thinking:
            payload["chat_template_kwargs"] = {
                "clear_thinking": self._model.clear_thinking_value,
            }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.post(NVIDIA_API_URL, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            if exc.request is not None:
                exc.request.headers["Authorization"] = "Bearer [REDACTED]"
            raise NvidiaClientError(
                NvidiaErrorCode.TIMEOUT,
                "The NVIDIA request timed out.",
            ) from None
        except httpx.HTTPError as exc:
            if exc.request is not None:
                exc.request.headers["Authorization"] = "Bearer [REDACTED]"
            raise NvidiaClientError(
                NvidiaErrorCode.PROVIDER_ERROR,
                "The NVIDIA request could not be completed.",
            ) from None

        if response.status_code < 200 or response.status_code >= 300:
            raise _http_error(response.status_code)

        try:
            data = response.json()
        except ValueError as exc:
            raise NvidiaClientError(
                NvidiaErrorCode.PROVIDER_ERROR,
                "NVIDIA returned malformed JSON.",
                status_code=response.status_code,
            ) from exc

        try:
            choice = data["choices"][0]
            message = choice["message"]
            content = message["content"]
            finish_reason = choice.get("finish_reason")
        except (KeyError, IndexError, TypeError) as exc:
            raise NvidiaClientError(
                NvidiaErrorCode.EMPTY_RESPONSE,
                "NVIDIA returned no usable visible answer.",
                status_code=response.status_code,
            ) from exc

        if finish_reason == "length":
            raise NvidiaClientError(
                NvidiaErrorCode.TRUNCATED_RESPONSE,
                "NVIDIA stopped because the output token limit was reached.",
                status_code=response.status_code,
            )
        if not isinstance(content, str) or not content.strip():
            raise NvidiaClientError(
                NvidiaErrorCode.EMPTY_RESPONSE,
                "NVIDIA returned no usable visible answer.",
                status_code=response.status_code,
            )
        return NvidiaChatResult(
            content=content.strip(),
            finish_reason=finish_reason if isinstance(finish_reason, str) else None,
            http_status=response.status_code,
        )
