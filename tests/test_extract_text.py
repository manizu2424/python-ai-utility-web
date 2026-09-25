import asyncio
from io import BytesIO
from threading import get_ident

import pytest
from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile

from app.config import get_settings
from app.main import app
from app.routers import text as text_router
from tests.test_pdf_converter import make_docx, make_pdf


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


def test_extract_text_rejects_file_with_mismatched_content(client: TestClient) -> None:
    response = client.post(
        "/api/extract-text",
        files={"file": ("renamed.pdf", b"not really a PDF", "application/pdf")},
    )

    assert response.status_code == 400
    assert "파일 내용" in response.json()["detail"]


def test_extract_text_rejects_oversized_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("RESULT_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("MAX_UPLOAD_MB", "0")
    get_settings.cache_clear()
    client = TestClient(app)

    try:
        response = client.post(
            "/api/extract-text",
            files={"file": ("large.txt", b"x", "text/plain")},
        )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 413
    assert "파일 크기" in response.json()["detail"]


def test_extract_text_reads_pdf_upload(client: TestClient) -> None:
    response = client.post(
        "/api/extract-text",
        files={"file": ("sample.pdf", make_pdf("pdf body text"), "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["text"] == "pdf body text"


def test_extract_text_reads_docx_upload(client: TestClient) -> None:
    response = client.post(
        "/api/extract-text",
        files={
            "file": (
                "sample.docx",
                make_docx("docx paragraph"),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["text"] == "docx paragraph"


def test_extract_text_returns_ocr_text_for_images(
    client: TestClient,
    monkeypatch,
) -> None:
    import pytesseract
    from PIL import Image

    image_buffer = BytesIO()
    Image.new("RGB", (20, 20), "white").save(image_buffer, format="PNG")
    captured: dict[str, object] = {}

    def fake_image_to_string(image, lang: str) -> str:
        captured["lang"] = lang
        captured["size"] = image.size
        return "  인식된 텍스트 OCR\n"

    monkeypatch.setattr(pytesseract, "image_to_string", fake_image_to_string)
    response = client.post(
        "/api/extract-text",
        files={"file": ("sample.png", image_buffer.getvalue(), "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["text"] == "인식된 텍스트 OCR"
    assert captured == {"lang": "kor+eng", "size": (20, 20)}


def test_extract_text_runs_extraction_outside_event_loop(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("RESULT_DIR", str(tmp_path / "results"))
    get_settings.cache_clear()
    worker_thread_id = None

    def fake_extract_text(path, extension: str) -> str:
        nonlocal worker_thread_id
        worker_thread_id = get_ident()
        return "extracted"

    monkeypatch.setattr(text_router, "extract_text", fake_extract_text)

    async def extract() -> tuple[int, dict[str, object]]:
        event_loop_thread_id = get_ident()
        upload = UploadFile(file=BytesIO(b"hello"), filename="sample.txt")
        payload = await text_router.extract_text_from_upload(upload)
        return event_loop_thread_id, payload

    try:
        event_loop_thread_id, payload = asyncio.run(extract())
    finally:
        get_settings.cache_clear()

    assert payload["text"] == "extracted"
    assert worker_thread_id is not None
    assert worker_thread_id != event_loop_thread_id


def test_extract_text_reports_missing_tesseract(
    client: TestClient,
    monkeypatch,
) -> None:
    import pytesseract
    from PIL import Image

    image_buffer = BytesIO()
    Image.new("RGB", (20, 20), "white").save(image_buffer, format="PNG")

    def raise_missing_tesseract(*args, **kwargs):
        raise pytesseract.TesseractNotFoundError()

    monkeypatch.setattr(pytesseract, "image_to_string", raise_missing_tesseract)
    response = client.post(
        "/api/extract-text",
        files={"file": ("sample.png", image_buffer.getvalue(), "image/png")},
    )

    assert response.status_code == 422
    assert "Tesseract OCR 실행 파일" in response.json()["detail"]
