import asyncio
from io import BytesIO
from threading import get_ident
from zipfile import ZipFile

import fitz
import pytest
from fastapi.testclient import TestClient
from docx import Document

from app.config import get_settings
from app.main import app
from app.routers.pdf import save_conversion_result


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("RESULT_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("MAX_UPLOAD_MB", "2")
    get_settings.cache_clear()
    yield TestClient(app)
    get_settings.cache_clear()


def make_pdf(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    content = document.tobytes()
    document.close()
    return content


def make_docx(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def upload_pdf(client: TestClient, endpoint: str, content: bytes) -> dict:
    response = client.post(
        endpoint,
        files={"file": ("sample.pdf", content, "application/pdf")},
    )
    assert response.status_code == 200
    return response.json()


def download_result(client: TestClient, payload: dict) -> bytes:
    response = client.get(payload["download_url"])
    assert response.status_code == 200
    return response.content


def test_pdf_to_images_returns_zip(client: TestClient) -> None:
    payload = upload_pdf(client, "/api/pdf/to-images", make_pdf("hello"))

    archive = ZipFile(BytesIO(download_result(client, payload)))
    assert "page-1.png" in archive.namelist()


def test_pdf_to_docx_returns_document(client: TestClient) -> None:
    payload = upload_pdf(client, "/api/pdf/to-docx", make_pdf("hello docx"))
    content = download_result(client, payload)

    assert content.startswith(b"PK")


def test_pdf_to_xlsx_returns_workbook(client: TestClient) -> None:
    payload = upload_pdf(client, "/api/pdf/to-xlsx", make_pdf("hello xlsx"))
    content = download_result(client, payload)

    assert content.startswith(b"PK")


def test_text_file_to_pdf_returns_pdf(client: TestClient) -> None:
    response = client.post(
        "/api/pdf/from-file",
        files={"file": ("sample.txt", b"hello pdf", "text/plain")},
    )

    assert response.status_code == 200
    content = download_result(client, response.json())
    with fitz.open(stream=content, filetype="pdf") as document:
        assert document.page_count == 1
        assert "hello pdf" in document[0].get_text()


def test_image_file_to_pdf_returns_pdf(client: TestClient) -> None:
    from PIL import Image

    image_buffer = BytesIO()
    Image.new("RGB", (100, 100), "white").save(image_buffer, format="PNG")

    response = client.post(
        "/api/pdf/from-file",
        files={"file": ("sample.png", image_buffer.getvalue(), "image/png")},
    )

    assert response.status_code == 200
    content = download_result(client, response.json())
    with fitz.open(stream=content, filetype="pdf") as document:
        assert document.page_count == 1


def test_docx_file_to_pdf_returns_pdf(client: TestClient) -> None:
    response = client.post(
        "/api/pdf/from-file",
        files={
            "file": (
                "sample.docx",
                make_docx("hello from docx"),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    content = download_result(client, response.json())
    with fitz.open(stream=content, filetype="pdf") as document:
        assert document.page_count == 1
        assert "hello from docx" in document[0].get_text()


def test_invalid_docx_to_pdf_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/pdf/from-file",
        files={
            "file": (
                "broken.docx",
                b"not a docx file",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 400
    assert "파일 내용" in response.json()["detail"]


def test_file_to_pdf_rejects_pdf_input(client: TestClient) -> None:
    response = client.post(
        "/api/pdf/from-file",
        files={"file": ("sample.pdf", make_pdf("already pdf"), "application/pdf")},
    )

    assert response.status_code == 400
    assert "지원하지 않는 파일 형식" in response.json()["detail"]


def test_merge_pdfs_returns_two_page_pdf(client: TestClient) -> None:
    response = client.post(
        "/api/pdf/merge",
        files=[
            ("files", ("a.pdf", make_pdf("first"), "application/pdf")),
            ("files", ("b.pdf", make_pdf("second"), "application/pdf")),
        ],
    )

    assert response.status_code == 200
    content = download_result(client, response.json())
    with fitz.open(stream=content, filetype="pdf") as document:
        assert document.page_count == 2


def test_split_pdf_returns_selected_page(client: TestClient) -> None:
    document = fitz.open()
    document.new_page().insert_text((72, 72), "first")
    document.new_page().insert_text((72, 72), "second")
    content = document.tobytes()
    document.close()

    response = client.post(
        "/api/pdf/split",
        data={"start_page": "2", "end_page": "2"},
        files={"file": ("sample.pdf", content, "application/pdf")},
    )

    assert response.status_code == 200
    with fitz.open(stream=download_result(client, response.json()), filetype="pdf") as result:
        assert result.page_count == 1
        assert "second" in result[0].get_text()


def test_split_pdf_rejects_invalid_range(client: TestClient) -> None:
    response = client.post(
        "/api/pdf/split",
        data={"start_page": "2", "end_page": "1"},
        files={"file": ("sample.pdf", make_pdf("bad range"), "application/pdf")},
    )

    assert response.status_code == 422
    assert "페이지 범위" in response.json()["detail"]


def test_compress_pdf_returns_readable_pdf(client: TestClient) -> None:
    payload = upload_pdf(client, "/api/pdf/compress", make_pdf("compress me"))
    content = download_result(client, payload)

    with fitz.open(stream=content, filetype="pdf") as document:
        assert document.page_count == 1
        assert "compress me" in document[0].get_text()


def test_conversion_factory_runs_outside_event_loop(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("RESULT_DIR", str(tmp_path / "results"))
    get_settings.cache_clear()
    worker_thread_id = None

    def make_content() -> bytes:
        nonlocal worker_thread_id
        worker_thread_id = get_ident()
        return b"converted"

    async def convert() -> tuple[int, dict[str, object]]:
        event_loop_thread_id = get_ident()
        payload = await save_conversion_result(
            make_content,
            ".pdf",
            "완료",
        )
        return event_loop_thread_id, payload

    event_loop_thread_id, payload = asyncio.run(convert())

    assert worker_thread_id is not None
    assert worker_thread_id != event_loop_thread_id
    assert payload["download_url"].startswith("/api/results/")
    get_settings.cache_clear()
