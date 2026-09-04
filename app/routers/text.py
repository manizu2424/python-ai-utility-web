from fastapi import APIRouter, File, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.services.cleanup import cleanup_runtime_files
from app.services.storage import save_text_result, save_upload
from app.services.text_extractor import TextExtractionError, extract_text


router = APIRouter(prefix="/api")


@router.post("/extract-text")
async def extract_text_from_upload(file: UploadFile = File(...)) -> dict[str, object]:
    settings = get_settings()
    await run_in_threadpool(cleanup_runtime_files, settings)
    stored_file = await save_upload(file, settings)

    try:
        text = await run_in_threadpool(
            extract_text,
            stored_file.path,
            stored_file.extension,
        )
    except TextExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    result_id = await run_in_threadpool(save_text_result, text, settings)
    return {
        "filename": stored_file.original_filename,
        "size": stored_file.size,
        "extension": stored_file.extension,
        "characters": len(text),
        "result_id": result_id,
        "download_url": f"/api/results/{result_id}",
        "text": text,
    }
