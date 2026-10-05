"""FastAPI entry point for Tiger-ZiWei."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.chart import router as chart_router

app = FastAPI(title="Tiger-ZiWei")
STATIC_DIR = Path(__file__).resolve().parent / "static"

app.include_router(chart_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
def health() -> dict[str, str]:
    """Return a deterministic application health response."""
    return {"status": "ok", "project": "Tiger-ZiWei"}


@app.get("/ziwei", include_in_schema=False)
def ziwei_page() -> FileResponse:
    """Serve the local, dependency-free chart interface."""

    return FileResponse(STATIC_DIR / "ziwei.html")
