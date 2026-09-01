import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("RESULT_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    get_settings.cache_clear()
    yield TestClient(app)
    get_settings.cache_clear()


def test_extract_text_upload_returns_result(client: TestClient) -> None:
    response = client.post(
        "/api/extract-text",
        files={"file": ("sample.txt", b"hello\nworld", "text/plain")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "sample.txt"
    assert payload["extension"] == ".txt"
    assert payload["text"] == "hello\nworld"
    assert payload["characters"] == 11
    assert payload["download_url"].startswith("/api/results/")

    download = client.get(payload["download_url"])
    assert download.status_code == 200
    assert download.text == "hello\nworld"


def test_extract_text_rejects_unsupported_extension(client: TestClient) -> None:
    response = client.post(
        "/api/extract-text",
        files={"file": ("sample.exe", b"not allowed", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "지원하지 않는 파일 형식" in response.json()["detail"]


def test_extract_text_rejects_oversized_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("RESULT_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("MAX_UPLOAD_MB", "0")
    get_settings.cache_clear()
    client = TestClient(app)

    response = client.post(
        "/api/extract-text",
        files={"file": ("large.txt", b"x", "text/plain")},
    )

    assert response.status_code == 413
    assert "파일 크기" in response.json()["detail"]
