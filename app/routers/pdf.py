from collections.abc import Callable

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.config import (
    SUPPORTED_PDF_EXTENSIONS,
    SUPPORTED_TO_PDF_EXTENSIONS,
    get_settings,
)
from app.services.cleanup import cleanup_runtime_files
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
from app.services.storage import StoredFile, save_result_bytes, save_upload


router = APIRouter(prefix="/api/pdf")


@router.post("/to-images")
async def convert_pdf_to_images(file: UploadFile = File(...)) -> dict[str, object]:
    stored_file = await save_pdf_upload(file)
    return await save_conversion_result(
        lambda: pdf_to_images_zip(stored_file.path),
        ".zip",
        "PDF 이미지 변환이 완료되었습니다.",
    )


@router.post("/to-docx")
async def convert_pdf_to_docx(file: UploadFile = File(...)) -> dict[str, object]:
    stored_file = await save_pdf_upload(file)
    return await save_conversion_result(
        lambda: pdf_to_docx(stored_file.path),
        ".docx",
        "PDF Word 변환이 완료되었습니다.",
    )


@router.post("/to-xlsx")
async def convert_pdf_to_xlsx(file: UploadFile = File(...)) -> dict[str, object]:
    stored_file = await save_pdf_upload(file)
    return await save_conversion_result(
        lambda: pdf_to_xlsx(stored_file.path),
        ".xlsx",
        "PDF Excel 변환이 완료되었습니다.",
    )


@router.post("/from-file")
async def convert_file_to_pdf(file: UploadFile = File(...)) -> dict[str, object]:
    settings = get_settings()
    await run_in_threadpool(cleanup_runtime_files, settings)
    stored_file = await save_upload(file, settings, SUPPORTED_TO_PDF_EXTENSIONS)
    return await save_conversion_result(
        lambda: file_to_pdf(stored_file.path, stored_file.extension),
        ".pdf",
        "PDF 생성이 완료되었습니다.",
    )


@router.post("/merge")
async def merge_pdf_files(files: list[UploadFile] = File(...)) -> dict[str, object]:
    if len(files) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF 병합에는 파일이 2개 이상 필요합니다.",
        )

    stored_files = [await save_pdf_upload(file) for file in files]
    return await save_conversion_result(
        lambda: merge_pdfs([stored_file.path for stored_file in stored_files]),
        ".pdf",
        "PDF 병합이 완료되었습니다.",
    )


@router.post("/split")
async def split_pdf_file(
    file: UploadFile = File(...),
    start_page: int = Form(...),
    end_page: int = Form(...),
) -> dict[str, object]:
    stored_file = await save_pdf_upload(file)
    return await save_conversion_result(
        lambda: split_pdf(stored_file.path, start_page, end_page),
        ".pdf",
        "PDF 분할이 완료되었습니다.",
    )


@router.post("/compress")
async def compress_pdf_file(file: UploadFile = File(...)) -> dict[str, object]:
    stored_file = await save_pdf_upload(file)
    return await save_conversion_result(
        lambda: compress_pdf(stored_file.path),
        ".pdf",
        "PDF 압축이 완료되었습니다.",
    )


async def save_pdf_upload(file: UploadFile) -> StoredFile:
    settings = get_settings()
    await run_in_threadpool(cleanup_runtime_files, settings)
    return await save_upload(file, settings, SUPPORTED_PDF_EXTENSIONS)


async def save_conversion_result(
    content_factory: Callable[[], bytes],
    extension: str,
    message: str,
) -> dict[str, object]:
    settings = get_settings()
    try:
        content = await run_in_threadpool(content_factory)
        result_id = await run_in_threadpool(
            save_result_bytes,
            content,
            extension,
            settings,
        )
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
