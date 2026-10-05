"""HTTP endpoint for deterministic Zi Wei chart calculation."""

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.chart import render_chart_png
from app.models.basic_chart import BasicChartResult
from app.models.birth import BirthData
from app.ziwei import calculate_basic_chart


router = APIRouter()


@router.post("/api/chart", response_model=BasicChartResult)
def calculate_chart(birth_data: BirthData) -> BasicChartResult:
    """Return the chart produced by the existing deterministic engine."""

    return calculate_basic_chart(birth_data)


@router.post("/api/chart/png", response_class=FileResponse)
def calculate_chart_png(birth_data: BirthData) -> FileResponse:
    """Render the existing deterministic chart and return its PNG file."""

    chart = calculate_basic_chart(birth_data)
    rendered = render_chart_png(chart)
    return FileResponse(
        rendered.path,
        media_type="image/png",
        filename=rendered.filename,
    )
