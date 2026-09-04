import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from app.config import SUPPORTED_PDF_EXTENSIONS, SUPPORTED_TO_PDF_EXTENSIONS, get_settings
from app.services.cleanup import cleanup_runtime_files, run_cleanup_loop
from app.services.pdf_converter import (
    PdfConversionError,
    compress_pdf,
    file_to_pdf,
    merge_pdfs,
    pdf_to_docx,
    pdf_to_images_zip,
    pdf_to_xlsx,
    split_pdf,
)
from app.services.storage import get_result_file, save_result_bytes, save_text_result, save_upload
from app.services.text_extractor import TextExtractionError, extract_text
from app.services.youtube_downloader import YoutubeDownloadError, download_youtube
from app.services.youtube_transcript import (
    YoutubeTranscriptError,
    extract_youtube_transcript,
)


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    cleanup_runtime_files(settings)
    cleanup_task = asyncio.create_task(run_cleanup_loop(settings))
    try:
        yield
    finally:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task


app = FastAPI(title="AI Utility Toolbox", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/extract-text")
async def extract_text_from_upload(file: UploadFile = File(...)) -> dict[str, object]:
    settings = get_settings()
    cleanup_runtime_files(settings)

    stored_file = await save_upload(file, settings)

    try:
        text = extract_text(stored_file.path, stored_file.extension)
    except TextExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    result_id = save_text_result(text, settings)

    return {
        "filename": stored_file.original_filename,
        "size": stored_file.size,
        "extension": stored_file.extension,
        "characters": len(text),
        "result_id": result_id,
        "download_url": f"/api/results/{result_id}",
        "text": text,
    }


@app.post("/api/pdf/to-images")
async def convert_pdf_to_images(file: UploadFile = File(...)) -> dict[str, object]:
    stored_file = await save_pdf_upload(file)
    return save_conversion_result(
        lambda: pdf_to_images_zip(stored_file.path),
        ".zip",
        "PDF 이미지 변환이 완료되었습니다.",
    )


@app.post("/api/pdf/to-docx")
async def convert_pdf_to_docx(file: UploadFile = File(...)) -> dict[str, object]:
    stored_file = await save_pdf_upload(file)
    return save_conversion_result(
        lambda: pdf_to_docx(stored_file.path),
        ".docx",
        "PDF Word 변환이 완료되었습니다.",
    )


@app.post("/api/pdf/to-xlsx")
async def convert_pdf_to_xlsx(file: UploadFile = File(...)) -> dict[str, object]:
    stored_file = await save_pdf_upload(file)
    return save_conversion_result(
        lambda: pdf_to_xlsx(stored_file.path),
        ".xlsx",
        "PDF Excel 변환이 완료되었습니다.",
    )


@app.post("/api/pdf/from-file")
async def convert_file_to_pdf(file: UploadFile = File(...)) -> dict[str, object]:
    settings = get_settings()
    cleanup_runtime_files(settings)
    stored_file = await save_upload(file, settings, SUPPORTED_TO_PDF_EXTENSIONS)
    return save_conversion_result(
        lambda: file_to_pdf(stored_file.path, stored_file.extension),
        ".pdf",
        "PDF 생성이 완료되었습니다.",
    )


@app.post("/api/pdf/merge")
async def merge_pdf_files(files: list[UploadFile] = File(...)) -> dict[str, object]:
    if len(files) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF 병합에는 파일이 2개 이상 필요합니다.",
        )

    stored_files = [await save_pdf_upload(file) for file in files]
    return save_conversion_result(
        lambda: merge_pdfs([stored_file.path for stored_file in stored_files]),
        ".pdf",
        "PDF 병합이 완료되었습니다.",
    )


@app.post("/api/pdf/split")
async def split_pdf_file(
    file: UploadFile = File(...),
    start_page: int = Form(...),
    end_page: int = Form(...),
) -> dict[str, object]:
    stored_file = await save_pdf_upload(file)
    return save_conversion_result(
        lambda: split_pdf(stored_file.path, start_page, end_page),
        ".pdf",
        "PDF 분할이 완료되었습니다.",
    )


@app.post("/api/pdf/compress")
async def compress_pdf_file(file: UploadFile = File(...)) -> dict[str, object]:
    stored_file = await save_pdf_upload(file)
    return save_conversion_result(
        lambda: compress_pdf(stored_file.path),
        ".pdf",
        "PDF 압축이 완료되었습니다.",
    )


@app.post("/api/youtube/download")
async def download_youtube_media(
    url: str = Form(...),
    mode: str = Form(...),
) -> dict[str, object]:
    settings = get_settings()
    cleanup_runtime_files(settings)

    try:
        result = await run_in_threadpool(download_youtube, url, mode, settings)
    except YoutubeDownloadError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return {
        "message": "유튜브 다운로드가 완료되었습니다.",
        "title": result.title,
        "duration": result.duration,
        "extension": result.extension,
        "size": result.size,
        "mode": result.mode,
        "result_id": result.result_id,
        "download_url": f"/api/results/{result.result_id}",
    }


@app.post("/api/youtube/transcript")
async def extract_youtube_transcript_text(
    url: str = Form(...),
    language: str = Form("auto"),
) -> dict[str, object]:
    settings = get_settings()
    cleanup_runtime_files(settings)

    try:
        transcript = await run_in_threadpool(
            extract_youtube_transcript,
            url,
            language,
            settings,
        )
    except YoutubeTranscriptError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    result_id = save_text_result(transcript.text, settings)
    return {
        "message": "유튜브 자막 추출이 완료되었습니다.",
        "title": transcript.title,
        "duration": transcript.duration,
        "language": transcript.language,
        "characters": len(transcript.text),
        "text": transcript.text,
        "result_id": result_id,
        "download_url": f"/api/results/{result_id}",
    }


@app.get("/api/results/{result_id}")
def download_result(result_id: str) -> FileResponse:
    settings = get_settings()
    result_file = get_result_file(result_id, settings)
    return FileResponse(
        result_file.path,
        media_type=result_file.media_type,
        filename=result_file.filename,
    )


async def save_pdf_upload(file: UploadFile):
    settings = get_settings()
    cleanup_runtime_files(settings)
    return await save_upload(file, settings, SUPPORTED_PDF_EXTENSIONS)


def save_conversion_result(
    content_factory: Callable[[], bytes],
    extension: str,
    message: str,
) -> dict[str, object]:
    settings = get_settings()
    try:
        content = content_factory()
        result_id = save_result_bytes(content, extension, settings)
    except PdfConversionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return {
        "message": message,
        "result_id": result_id,
        "download_url": f"/api/results/{result_id}",
    }
