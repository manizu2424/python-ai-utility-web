from fastapi import APIRouter, Form, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.services.cleanup import cleanup_runtime_files
from app.services.storage import save_text_result
from app.services.youtube_downloader import YoutubeDownloadError, download_youtube
from app.services.youtube_transcript import (
    YoutubeTranscriptError,
    extract_youtube_transcript,
)


router = APIRouter(prefix="/api/youtube")


@router.post("/download")
async def download_youtube_media(
    url: str = Form(...),
    mode: str = Form(...),
) -> dict[str, object]:
    settings = get_settings()
    await run_in_threadpool(cleanup_runtime_files, settings)

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


@router.post("/transcript")
async def extract_youtube_transcript_text(
    url: str = Form(...),
    language: str = Form("auto"),
) -> dict[str, object]:
    settings = get_settings()
    await run_in_threadpool(cleanup_runtime_files, settings)

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

    result_id = await run_in_threadpool(save_text_result, transcript.text, settings)
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
