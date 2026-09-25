import importlib
import sys

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_index_returns_html() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_index_requires_revalidation_so_new_assets_load() -> None:
    response = client.get("/")

    assert response.headers["cache-control"] == "no-cache"


@pytest.fixture
def load_app(monkeypatch):
    """Re-import app.main under a given APP_ENV, since docs URLs are fixed at import."""

    def _load(app_env: str):
        monkeypatch.setenv("APP_ENV", app_env)
        return importlib.reload(sys.modules["app.main"]).app

    yield _load
    monkeypatch.delenv("APP_ENV", raising=False)
    importlib.reload(sys.modules["app.main"])


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_api_docs_hidden_in_production(load_app, path) -> None:
    production_client = TestClient(load_app("production"))

    assert production_client.get(path).status_code == 404
    assert production_client.get("/health").status_code == 200


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_api_docs_available_in_development(load_app, path) -> None:
    development_client = TestClient(load_app("development"))

    assert development_client.get(path).status_code == 200
