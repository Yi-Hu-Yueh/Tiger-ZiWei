"""Structured interpretation endpoints for verified Flow-Month and Flow-Day layers."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.chart import _PROVIDER_ERROR_DETAILS, _calculate_input_chart
from app.api.llm_request import LLMRequestSelection, attach_llm_metadata, resolve_llm_request_selection
from app.llm.flow_period_interpreter import (
    FlowDayInterpreter,
    FlowMonthInterpreter,
    FlowPeriodInterpretationParseError,
)
from app.llm.interpreter import INTERPRETATION_TIMEOUT_SECONDS
from app.llm.nvidia_client import NvidiaClientError
from app.models.flow_period_interpretation import (
    FlowDayInterpretationRequest,
    FlowDayInterpretationResult,
    FlowMonthInterpretationRequest,
    FlowMonthInterpretationResult,
)
from app.ziwei.flow_query import calculate_flow_query


router = APIRouter()


def _provider_error(exc: NvidiaClientError) -> HTTPException:
    status_code, message = _PROVIDER_ERROR_DETAILS[exc.code]
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code.value, "message": message},
    )


@router.post(
    "/api/flow-month/interpret",
    response_model=FlowMonthInterpretationResult,
    response_model_exclude_none=True,
)
async def interpret_flow_month(
    request: FlowMonthInterpretationRequest,
    selection: LLMRequestSelection = Depends(resolve_llm_request_selection),
) -> FlowMonthInterpretationResult:
    chart = _calculate_input_chart(request.birth_input)
    try:
        result = calculate_flow_query(chart, request.query)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_FLOW_MONTH", "message": str(exc)},
        ) from None
    if result.flow_month is None:
        raise HTTPException(
            status_code=422,
            detail={"code": "FLOW_MONTH_REQUIRED", "message": "流月解讀需要農曆月份。"},
        )
    try:
        interpreted = await selection.configure_interpreter(
            FlowMonthInterpreter(), timeout=INTERPRETATION_TIMEOUT_SECONDS
        ).interpret(chart, result.flow_year, result.flow_month)
        return attach_llm_metadata(interpreted, selection)
    except NvidiaClientError as exc:
        raise _provider_error(exc) from None
    except FlowPeriodInterpretationParseError:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "INVALID_STRUCTURED_RESPONSE",
                "message": "NVIDIA API 回傳的流月解讀格式無效，請稍後再試。",
            },
        ) from None


@router.post(
    "/api/flow-day/interpret",
    response_model=FlowDayInterpretationResult,
    response_model_exclude_none=True,
)
async def interpret_flow_day(
    request: FlowDayInterpretationRequest,
    selection: LLMRequestSelection = Depends(resolve_llm_request_selection),
) -> FlowDayInterpretationResult:
    chart = _calculate_input_chart(request.birth_input)
    try:
        result = calculate_flow_query(chart, request.query)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_FLOW_DAY", "message": str(exc)},
        ) from None
    if result.flow_month is None or result.flow_day is None:
        raise HTTPException(
            status_code=422,
            detail={"code": "FLOW_DAY_REQUIRED", "message": "流日解讀需要完整農曆日期。"},
        )
    try:
        interpreted = await selection.configure_interpreter(
            FlowDayInterpreter(), timeout=INTERPRETATION_TIMEOUT_SECONDS
        ).interpret(
            chart, result.flow_year, result.flow_month, result.flow_day
        )
        return attach_llm_metadata(interpreted, selection)
    except NvidiaClientError as exc:
        raise _provider_error(exc) from None
    except FlowPeriodInterpretationParseError:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "INVALID_STRUCTURED_RESPONSE",
                "message": "NVIDIA API 回傳的流日解讀格式無效，請稍後再試。",
            },
        ) from None
