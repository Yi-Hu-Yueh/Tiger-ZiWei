"""HTTP endpoints for deterministic chart calculation and interpretation."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.llm_request import LLMRequestSelection, attach_llm_metadata, resolve_llm_request_selection
from app.birth_input import BirthInputConversionError, normalize_birth_input
from app.chart import render_chart_png
from app.llm.interpreter import (
    INTERPRETATION_TIMEOUT_SECONDS,
    InterpretationParseError,
    ZiweiInterpreter,
)
from app.llm.nvidia_client import NvidiaClientError, NvidiaErrorCode
from app.models.basic_chart import BasicChartResult
from app.models.birth import BirthInput
from app.models.interpretation import InterpretationResult
from app.ziwei import calculate_basic_chart


router = APIRouter()


_PROVIDER_ERROR_DETAILS: dict[NvidiaErrorCode, tuple[int, str]] = {
    NvidiaErrorCode.MISSING_API_KEY: (503, "NVIDIA API 金鑰尚未設定。"),
    NvidiaErrorCode.AUTHENTICATION_ERROR: (502, "NVIDIA API 驗證失敗，請確認金鑰設定。"),
    NvidiaErrorCode.PERMISSION_ERROR: (502, "NVIDIA API 權限不足，無法使用指定模型。"),
    NvidiaErrorCode.PAYMENT_OR_QUOTA_ERROR: (502, "NVIDIA API 額度或計費狀態無法完成解盤。"),
    NvidiaErrorCode.RATE_LIMIT_ERROR: (429, "NVIDIA API 請求過於頻繁，請稍後再試。"),
    NvidiaErrorCode.REQUEST_VALIDATION_ERROR: (502, "NVIDIA API 無法接受解盤請求。"),
    NvidiaErrorCode.PROVIDER_ERROR: (502, "NVIDIA API 暫時無法完成解盤。"),
    NvidiaErrorCode.TIMEOUT: (504, "NVIDIA API 回應逾時，請稍後再試。"),
    NvidiaErrorCode.EMPTY_RESPONSE: (502, "NVIDIA API 未回傳可用的解盤內容。"),
    NvidiaErrorCode.TRUNCATED_RESPONSE: (502, "NVIDIA API 回傳的解盤內容不完整。"),
}


def _calculate_input_chart(birth_input: BirthInput) -> BasicChartResult:
    try:
        birth_data = normalize_birth_input(birth_input)
    except BirthInputConversionError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_BIRTH_DATE", "message": str(exc)},
        ) from None
    return calculate_basic_chart(birth_data)


@router.post("/api/chart", response_model=BasicChartResult)
def calculate_chart(birth_input: BirthInput) -> BasicChartResult:
    """Return the chart produced by the existing deterministic engine."""

    return _calculate_input_chart(birth_input)


@router.post("/api/chart/png", response_class=FileResponse)
def calculate_chart_png(birth_input: BirthInput) -> FileResponse:
    """Render the existing deterministic chart and return its PNG file."""

    chart = _calculate_input_chart(birth_input)
    rendered = render_chart_png(chart)
    return FileResponse(
        rendered.path,
        media_type="image/png",
        filename=rendered.filename,
    )


@router.post(
    "/api/interpret",
    response_model=InterpretationResult,
    response_model_exclude_none=True,
)
async def interpret_chart(
    birth_input: BirthInput,
    selection: LLMRequestSelection = Depends(resolve_llm_request_selection),
) -> InterpretationResult:
    """Calculate the authoritative chart, then interpret it in one LLM call."""

    chart = _calculate_input_chart(birth_input)
    try:
        result = await selection.configure_interpreter(
            ZiweiInterpreter(), timeout=INTERPRETATION_TIMEOUT_SECONDS
        ).interpret(chart)
        return attach_llm_metadata(result, selection)
    except NvidiaClientError as exc:
        status_code, message = _PROVIDER_ERROR_DETAILS[exc.code]
        raise HTTPException(
            status_code=status_code,
            detail={"code": exc.code.value, "message": message},
        ) from None
    except InterpretationParseError:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "INVALID_STRUCTURED_RESPONSE",
                "message": "NVIDIA API 回傳的解盤格式無效，請稍後再試。",
            },
        ) from None
