"""HTTP endpoint for normalized Gregorian/lunar hierarchical flow queries."""

from fastapi import APIRouter, HTTPException

from app.api.chart import _calculate_input_chart
from app.models.flow_query import FlowQueryRequest, FlowQueryResult
from app.ziwei.flow_query import calculate_flow_query


router = APIRouter()


@router.post("/api/flow-query", response_model=FlowQueryResult)
def calculate_flow_query_endpoint(request: FlowQueryRequest) -> FlowQueryResult:
    chart = _calculate_input_chart(request.birth_input)
    try:
        return calculate_flow_query(chart, request.query)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_FLOW_QUERY", "message": str(exc)},
        ) from None
