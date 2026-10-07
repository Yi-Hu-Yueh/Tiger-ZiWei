"""One-request manual smoke validation for NVIDIA-hosted GLM-5.3-Flash."""

from __future__ import annotations

import asyncio

from app.config import (
    NVIDIA_API_URL,
    NVIDIA_CLEAR_THINKING,
    NVIDIA_MODEL,
    NVIDIA_REASONING_EFFORT,
)
from app.llm import NvidiaClient, NvidiaClientError


async def _validate() -> int:
    print("Provider: NVIDIA")
    print(f"Model: {NVIDIA_MODEL}")
    print(f"Endpoint: {NVIDIA_API_URL}")
    print(f"Reasoning effort: {NVIDIA_REASONING_EFFORT}")
    try:
        result = await NvidiaClient().chat_result(
            [{"role": "user", "content": "請只回答一句繁體中文：連線成功。"}],
            max_tokens=64,
        )
    except NvidiaClientError as exc:
        print("clear_thinking: NOT VERIFIED")
        print(f"HTTP status: {exc.status_code if exc.status_code is not None else 'NOT AVAILABLE'}")
        print(f"Result: {exc.code.value}")
        return 1

    print("clear_thinking: VERIFIED")
    print(f"HTTP status: {result.http_status}")
    print(f"Visible answer: {result.content}")
    print(f"finish_reason: {result.finish_reason or 'not provided'}")
    return 0


def main() -> int:
    return asyncio.run(_validate())


if __name__ == "__main__":
    raise SystemExit(main())
