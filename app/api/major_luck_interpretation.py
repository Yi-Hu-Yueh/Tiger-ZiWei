"""Focused API for structured interpretation of one selected Major-Luck."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.chart import _PROVIDER_ERROR_DETAILS, _calculate_input_chart
from app.api.llm_request import LLMRequestSelection, attach_llm_metadata, resolve_llm_request_selection
from app.llm.interpreter import INTERPRETATION_TIMEOUT_SECONDS
from app.llm.major_luck_interpreter import (
    MajorLuckInterpretationParseError,
    MajorLuckInterpreter,
)
from app.llm.nvidia_client import NvidiaClientError
from app.models.major_luck_interpretation import (
    MajorLuckInterpretationRequest,
    MajorLuckInterpretationResult,
)


router = APIRouter()


@router.post(
    "/api/major-luck/interpret",
    response_model=MajorLuckInterpretationResult,
    response_model_exclude_none=True,
)
async def interpret_major_luck(
    request: MajorLuckInterpretationRequest,
    selection: LLMRequestSelection = Depends(resolve_llm_request_selection),
) -> MajorLuckInterpretationResult:
    """Rebuild the chart and interpret exactly one verified 1-based period."""

    chart = _calculate_input_chart(request.birth_input)
    try:
        result = await selection.configure_interpreter(
            MajorLuckInterpreter(), timeout=INTERPRETATION_TIMEOUT_SECONDS
        ).interpret(chart, request.major_luck_index)
        return attach_llm_metadata(result, selection)
    except NvidiaClientError as exc:
        status_code, message = _PROVIDER_ERROR_DETAILS[exc.code]
        raise HTTPException(
            status_code=status_code,
            detail={"code": exc.code.value, "message": message},
        ) from None
    except MajorLuckInterpretationParseError:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "INVALID_STRUCTURED_RESPONSE",
                "message": "NVIDIA API 回傳的大限解讀格式無效，請稍後再試。",
            },
        ) from None
