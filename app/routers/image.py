from fastapi import APIRouter, Form, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.services.cleanup import cleanup_runtime_files
from app.services.comfyui_client import (
    IMAGE_SIZES,
    ComfyUIError,
    ComfyUITimeoutError,
    ComfyUIUnavailableError,
    generate_image,
)
from app.services.prompt_translator import (
    PromptTranslationError,
    TranslationUnavailableError,
    translate_prompt,
)
from app.services.storage import save_result_bytes


MAX_PROMPT_CHARS = 2000

router = APIRouter(prefix="/api/image")


def clean_prompt(prompt: str) -> str:
    cleaned = prompt.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="프롬프트를 입력하세요.",
        )
    if len(cleaned) > MAX_PROMPT_CHARS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"프롬프트는 {MAX_PROMPT_CHARS}자 이하로 입력하세요.",
        )
    return cleaned


@router.post("/translate")
async def translate_image_prompt(prompt: str = Form("")) -> dict[str, str]:
    cleaned = clean_prompt(prompt)

    try:
        translated = await run_in_threadpool(translate_prompt, cleaned, get_settings())
    except TranslationUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except PromptTranslationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return {"prompt_en": translated}


@router.post("/generate")
async def generate_image_result(
    prompt: str = Form(""),
    size: str = Form("portrait"),
) -> dict[str, object]:
    cleaned = clean_prompt(prompt)
    if size not in IMAGE_SIZES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="지원하지 않는 이미지 크기입니다.",
        )

    settings = get_settings()
    await run_in_threadpool(cleanup_runtime_files, settings)

    try:
        image = await run_in_threadpool(generate_image, cleaned, size, settings)
    except ComfyUIUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ComfyUITimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        ) from exc
    except ComfyUIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    result_id = await run_in_threadpool(save_result_bytes, image.content, ".png", settings)
    return {
        "message": "이미지 생성이 완료되었습니다.",
        "result_id": result_id,
        "download_url": f"/api/results/{result_id}",
        "seed": image.seed,
        "width": image.width,
        "height": image.height,
    }
