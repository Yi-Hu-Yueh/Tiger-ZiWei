"""HTTP endpoint for one explicit deterministic Flow-Year calculation."""

from fastapi import APIRouter, HTTPException

from app.api.chart import _calculate_input_chart
from app.models.flow_year import FlowYearRequest, FlowYearResult
from app.ziwei.flow_year import calculate_flow_year


router = APIRouter()


@router.post("/api/flow-year", response_model=FlowYearResult)
def calculate_flow_year_endpoint(request: FlowYearRequest) -> FlowYearResult:
    """Rebuild the authoritative natal chart and calculate one requested lunar year."""

    chart = _calculate_input_chart(request.birth_input)
    try:
        return calculate_flow_year(chart, request.target_year)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_FLOW_YEAR", "message": str(exc)},
        ) from None
