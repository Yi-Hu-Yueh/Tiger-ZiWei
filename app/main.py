"""FastAPI entry point for Tiger-ZiWei."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.chart import router as chart_router
from app.api.flow_year import router as flow_year_router
from app.api.flow_date import router as flow_date_router
from app.api.flow_query import router as flow_query_router
from app.api.flow_year_interpretation import router as flow_year_interpretation_router
from app.api.flow_period_interpretation import router as flow_period_interpretation_router
from app.api.major_luck_interpretation import router as major_luck_interpretation_router
from app.api.llm_models import router as llm_models_router
from app.api.report import router as report_router

app = FastAPI(title="Tiger-ZiWei")
STATIC_DIR = Path(__file__).resolve().parent / "static"

app.include_router(chart_router)
app.include_router(flow_year_router)
app.include_router(flow_date_router)
app.include_router(flow_query_router)
app.include_router(flow_year_interpretation_router)
app.include_router(flow_period_interpretation_router)
app.include_router(major_luck_interpretation_router)
app.include_router(llm_models_router)
app.include_router(report_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/ziwei", status_code=307)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a deterministic application health response."""
    return {"status": "ok", "project": "Tiger-ZiWei"}


@app.get("/ziwei", include_in_schema=False)
def ziwei_page() -> FileResponse:
    """Serve the local, dependency-free chart interface."""

    return FileResponse(STATIC_DIR / "ziwei.html")
