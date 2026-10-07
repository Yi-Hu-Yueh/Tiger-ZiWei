"""DOCX endpoint that rebuilds and fact-locks every supplied report layer."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.api.chart import _calculate_input_chart
from app.llm.flow_year_interpreter import (
    FlowYearInterpretationParseError,
    build_flow_year_interpretation_facts,
    validate_flow_year_fact_lock,
)
from app.llm.major_luck_interpreter import (
    MajorLuckInterpretationParseError,
    build_major_luck_interpretation_facts,
    validate_major_luck_fact_lock,
)
from app.llm.flow_period_interpreter import (
    FlowPeriodInterpretationParseError,
    build_flow_day_interpretation_facts,
    build_flow_month_interpretation_facts,
    validate_flow_day_fact_lock,
    validate_flow_month_fact_lock,
)
from app.models.report import ReportRequest
from app.report import render_word_report
from app.report.word_report import DOCX_MEDIA_TYPE
from app.ziwei.flow_year import calculate_flow_year
from app.ziwei.flow_date import calculate_flow_date
from app.ziwei.flow_query import calculate_flow_query


router = APIRouter()


@router.post("/api/report/docx", response_class=FileResponse)
def create_docx_report(request: ReportRequest) -> FileResponse:
    chart = _calculate_input_chart(request.birth_input)
    if {item.palace_name for item in request.interpretation.palace_interpretations} != {
        palace.palace_name for palace in chart.palaces
    }:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_NATAL_REPORT", "message": "本命解讀與命盤不一致。"},
        )

    major_luck_interpretation = None
    if request.major_luck_report is not None:
        try:
            facts = build_major_luck_interpretation_facts(
                chart,
                request.major_luck_report.major_luck_index,
            )
            validate_major_luck_fact_lock(facts, request.major_luck_report.interpretation)
        except (ValueError, MajorLuckInterpretationParseError):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "INVALID_MAJOR_LUCK_REPORT",
                    "message": "大限解讀已失效或與命盤不一致，請重新解讀。",
                },
            ) from None
        major_luck_interpretation = request.major_luck_report.interpretation

    flow_date = None
    flow_query = None
    flow_year = None
    if request.flow_query is not None:
        try:
            flow_query = calculate_flow_query(chart, request.flow_query)
            flow_year = flow_query.flow_year
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "INVALID_FLOW_QUERY_REPORT",
                    "message": "運限查詢已失效或與命盤不一致，請重新計算。",
                },
            ) from None
    elif request.target_datetime is not None:
        try:
            flow_date = calculate_flow_date(chart, request.target_datetime)
            flow_year = flow_date.flow_year
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "INVALID_FLOW_DATE_REPORT",
                    "message": "運限查詢時間已失效或與命盤不一致，請重新計算。",
                },
            ) from None
    elif request.target_flow_year is not None:
        try:
            flow_year = calculate_flow_year(chart, request.target_flow_year)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "INVALID_FLOW_YEAR_REPORT",
                    "message": "流年資料已失效或與命盤不一致，請重新計算。",
                },
            ) from None

    flow_year_interpretation = request.flow_year_interpretation
    if flow_year_interpretation is not None:
        if flow_year is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "INVALID_FLOW_YEAR_REPORT",
                    "message": "流年解讀缺少目前有效的流年資料。",
                },
            )
        try:
            facts = build_flow_year_interpretation_facts(chart, flow_year)
            validate_flow_year_fact_lock(facts, flow_year_interpretation)
        except (ValueError, FlowYearInterpretationParseError):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "INVALID_FLOW_YEAR_REPORT",
                    "message": "流年解讀已失效或與命盤不一致，請重新計算並解讀。",
                },
            ) from None

    flow_month_interpretation = request.flow_month_interpretation
    if flow_month_interpretation is not None:
        if flow_query is None or flow_query.flow_month is None:
            raise HTTPException(
                status_code=422,
                detail={"code": "INVALID_FLOW_MONTH_REPORT", "message": "流月解讀缺少目前有效的流月資料。"},
            )
        try:
            facts = build_flow_month_interpretation_facts(
                chart, flow_query.flow_year, flow_query.flow_month
            )
            validate_flow_month_fact_lock(facts, flow_month_interpretation)
        except (ValueError, FlowPeriodInterpretationParseError):
            raise HTTPException(
                status_code=422,
                detail={"code": "INVALID_FLOW_MONTH_REPORT", "message": "流月解讀已失效或與命盤不一致。"},
            ) from None

    flow_day_interpretation = request.flow_day_interpretation
    if flow_day_interpretation is not None:
        if flow_query is None or flow_query.flow_month is None or flow_query.flow_day is None:
            raise HTTPException(
                status_code=422,
                detail={"code": "INVALID_FLOW_DAY_REPORT", "message": "流日解讀缺少目前有效的流日資料。"},
            )
        try:
            facts = build_flow_day_interpretation_facts(
                chart, flow_query.flow_year, flow_query.flow_month, flow_query.flow_day
            )
            validate_flow_day_fact_lock(facts, flow_day_interpretation)
        except (ValueError, FlowPeriodInterpretationParseError):
            raise HTTPException(
                status_code=422,
                detail={"code": "INVALID_FLOW_DAY_REPORT", "message": "流日解讀已失效或與命盤不一致。"},
            ) from None

    report = render_word_report(
        chart,
        request.birth_input,
        request.interpretation,
        flow_date=flow_date,
        flow_query=flow_query,
        flow_year=flow_year,
        major_luck_interpretation=major_luck_interpretation,
        flow_year_interpretation=flow_year_interpretation,
        flow_month_interpretation=flow_month_interpretation,
        flow_day_interpretation=flow_day_interpretation,
    )
    return FileResponse(
        report.path,
        media_type=DOCX_MEDIA_TYPE,
        filename=report.filename,
    )
