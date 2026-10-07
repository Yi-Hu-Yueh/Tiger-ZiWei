"""Focused API for structured interpretation of one explicit Flow-Year."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.chart import _PROVIDER_ERROR_DETAILS, _calculate_input_chart
from app.api.llm_request import LLMRequestSelection, attach_llm_metadata, resolve_llm_request_selection
from app.llm.interpreter import INTERPRETATION_TIMEOUT_SECONDS
from app.llm.flow_year_interpreter import (
    FlowYearInterpretationParseError,
    FlowYearInterpreter,
)
from app.llm.nvidia_client import NvidiaClientError
from app.models.flow_year_interpretation import (
    FlowYearInterpretationRequest,
    FlowYearInterpretationResult,
)
from app.ziwei.flow_year import calculate_flow_year


router = APIRouter()


@router.post(
    "/api/flow-year/interpret",
    response_model=FlowYearInterpretationResult,
    response_model_exclude_none=True,
)
async def interpret_flow_year(
    request: FlowYearInterpretationRequest,
    selection: LLMRequestSelection = Depends(resolve_llm_request_selection),
) -> FlowYearInterpretationResult:
    """Rebuild the chart and interpret exactly one authoritative annual result."""

    chart = _calculate_input_chart(request.birth_input)
    try:
        flow_year = calculate_flow_year(chart, request.target_year)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_FLOW_YEAR", "message": str(exc)},
        ) from None
    try:
        result = await selection.configure_interpreter(
            FlowYearInterpreter(), timeout=INTERPRETATION_TIMEOUT_SECONDS
        ).interpret(chart, flow_year)
        return attach_llm_metadata(result, selection)
    except NvidiaClientError as exc:
        status_code, message = _PROVIDER_ERROR_DETAILS[exc.code]
        raise HTTPException(
            status_code=status_code,
            detail={"code": exc.code.value, "message": message},
        ) from None
    except FlowYearInterpretationParseError:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "INVALID_STRUCTURED_RESPONSE",
                "message": "NVIDIA API 回傳的流年解讀格式無效，請稍後再試。",
            },
        ) from None
