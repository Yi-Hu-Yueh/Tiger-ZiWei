"""HTTP endpoint for one explicit deterministic Flow-Date calculation."""

from fastapi import APIRouter, HTTPException

from app.api.chart import _calculate_input_chart
from app.models.flow_date import FlowDateRequest, FlowDateResult
from app.ziwei.flow_date import calculate_flow_date


router = APIRouter()


@router.post("/api/flow-date", response_model=FlowDateResult)
def calculate_flow_date_endpoint(request: FlowDateRequest) -> FlowDateResult:
    """Rebuild the natal chart and calculate all deterministic dynamic layers."""

    chart = _calculate_input_chart(request.birth_input)
    try:
        return calculate_flow_date(chart, request.target_datetime)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_FLOW_DATE", "message": str(exc)},
        ) from None
