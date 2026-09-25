import httpx

from app.config import Settings


OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
REQUEST_TIMEOUT_SECONDS = 60.0
# Z-Image Turbo (Qwen3 text encoder) follows natural sentences better than tag lists.
SYSTEM_PROMPT = (
    "You translate image-generation prompts into English for the Z-Image Turbo model. "
    "Write natural, descriptive English sentences, not comma-separated tags. "
    "Keep every subject, style, lighting, camera, and composition detail and do not add "
    "new content. If the input is already English, return it with only minimal fixes. "
    "Output only the prompt text, with no quotes, labels, or explanations."
)
QUOTE_CHARS = "\"'`“”‘’"


class PromptTranslationError(Exception):
    """Raised when the OpenAI translation request fails."""


class TranslationUnavailableError(PromptTranslationError):
    """Raised when translation is not configured on the server."""


def translate_prompt(
    text: str,
    settings: Settings,
    *,
    transport: httpx.BaseTransport | None = None,
) -> str:
    if not settings.openai_api_key:
        raise TranslationUnavailableError("서버에 OPENAI_API_KEY가 설정되지 않았습니다.")

    body = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    }
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}

    try:
        with httpx.Client(transport=transport, timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = client.post(OPENAI_CHAT_URL, json=body, headers=headers)
    except httpx.TransportError as exc:
        raise PromptTranslationError("OpenAI API에 연결할 수 없습니다.") from exc

    if response.status_code == 401:
        raise PromptTranslationError("OpenAI API 키가 올바르지 않습니다.")
    if response.status_code == 429:
        raise PromptTranslationError(
            "OpenAI API 사용 한도를 넘었거나 크레딧이 부족합니다."
        )
    if response.is_error:
        raise PromptTranslationError(
            f"OpenAI 번역 요청에 실패했습니다(HTTP {response.status_code})."
        )

    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise PromptTranslationError("OpenAI 응답 형식을 해석할 수 없습니다.") from exc

    translated = (content or "").strip().strip(QUOTE_CHARS).strip()
    if not translated:
        raise PromptTranslationError("OpenAI가 빈 번역 결과를 반환했습니다.")
    return translated
