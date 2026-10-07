"""Root landing-route regressions without any provider/network requests."""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.llm.nvidia_client import NvidiaClient
from app.main import app


@pytest.fixture(autouse=True)
def forbid_provider_requests(monkeypatch):
    async def forbidden(*args, **kwargs):
        pytest.fail("Routing tests must not make NVIDIA or external requests.")

    monkeypatch.setattr(NvidiaClient, "chat", forbidden)
    monkeypatch.setattr(NvidiaClient, "chat_result", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_root_redirect_status_and_exact_location(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/ziwei"


def test_ziwei_remains_html_without_redirect(client):
    response = client.get("/ziwei", follow_redirects=False)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "紫微斗數排盤" in response.text
    assert "location" not in response.headers


def test_health_remains_deterministic_without_redirect(client):
    response = client.get("/health", follow_redirects=False)
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "project": "Tiger-ZiWei"}
    assert "location" not in response.headers


def test_existing_api_routes_remain_registered(client):
    routes = {
        (method.upper(), path)
        for path, operations in client.get("/openapi.json").json()["paths"].items()
        for method in operations
    }
    expected = {("GET", "/api/llm/models")} | {
        ("POST", path)
        for path in (
            "/api/chart", "/api/chart/png", "/api/interpret",
            "/api/major-luck/interpret", "/api/flow-year", "/api/flow-date",
            "/api/flow-query", "/api/flow-year/interpret",
            "/api/flow-month/interpret", "/api/flow-day/interpret",
            "/api/report/docx",
        )
    }
    assert expected <= routes


def test_root_has_one_redirect_and_no_loop(client):
    response = client.get("/", follow_redirects=True)
    assert response.status_code == 200
    assert response.url.path == "/ziwei"
    assert len(response.history) == 1
    assert response.history[0].status_code == 307
    assert response.history[0].headers["location"] == "/ziwei"


def test_root_is_unique_and_excluded_from_openapi(client):
    root_routes = [route for route in app.routes if getattr(route, "path", None) == "/"]
    assert len(root_routes) == 1
    assert "/" not in client.get("/openapi.json").json()["paths"]


def test_chart_api_still_calculates_without_redirect_or_nvidia(client):
    response = client.post("/api/chart", json={
        "name": "Routing regression", "gender": "female",
        "birth_year": 2025, "birth_month": 1, "birth_day": 29,
        "birth_hour": 0, "birth_minute": 30, "birthplace": "Taipei",
    }, follow_redirects=False)
    assert response.status_code == 200
    assert "location" not in response.headers
    assert len(response.json()["palaces"]) == 12
