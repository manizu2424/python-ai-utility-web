import json

import httpx
import pytest

from app.config import Settings
from app.services.prompt_translator import (
    PromptTranslationError,
    TranslationUnavailableError,
    translate_prompt,
)


def make_settings(tmp_path, api_key: str | None = "sk-test") -> Settings:
    return Settings(
        upload_dir=tmp_path / "uploads",
        result_dir=tmp_path / "results",
        max_upload_mb=1,
        upload_retention_hours=24,
        result_retention_hours=24,
        cleanup_interval_minutes=60,
        youtube_max_download_mb=10,
        youtube_max_duration_seconds=7200,
        openai_api_key=api_key,
        openai_model="gpt-test",
    )


def openai_transport(
    response: httpx.Response,
    requests: list[httpx.Request] | None = None,
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if requests is not None:
            requests.append(request)
        return response

    return httpx.MockTransport(handler)


def chat_response(content: str | None) -> httpx.Response:
    return httpx.Response(
        200,
        json={"choices": [{"message": {"role": "assistant", "content": content}}]},
    )


def test_translate_prompt_returns_trimmed_english(tmp_path) -> None:
    requests: list[httpx.Request] = []

    translated = translate_prompt(
        "소파 위의 고양이",
        make_settings(tmp_path),
        transport=openai_transport(chat_response('  "A cat on a sofa."\n'), requests),
    )

    assert translated == "A cat on a sofa."
    request = requests[0]
    assert str(request.url) == "https://api.openai.com/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer sk-test"
    body = json.loads(request.content)
    assert body["model"] == "gpt-test"
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][1] == {"role": "user", "content": "소파 위의 고양이"}


def test_translate_prompt_requires_api_key(tmp_path) -> None:
    with pytest.raises(TranslationUnavailableError, match="OPENAI_API_KEY"):
        translate_prompt("고양이", make_settings(tmp_path, api_key=None))


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [(401, "키가 올바르지 않습니다"), (429, "한도"), (500, "HTTP 500")],
)
def test_translate_prompt_reports_http_errors(tmp_path, status_code, expected) -> None:
    with pytest.raises(PromptTranslationError, match=expected) as exc_info:
        translate_prompt(
            "고양이",
            make_settings(tmp_path),
            transport=openai_transport(httpx.Response(status_code, json={"error": {}})),
        )

    assert type(exc_info.value) is PromptTranslationError


def test_translate_prompt_reports_unreachable_api(tmp_path) -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(PromptTranslationError, match="연결할 수 없습니다"):
        translate_prompt(
            "고양이",
            make_settings(tmp_path),
            transport=httpx.MockTransport(refuse),
        )


@pytest.mark.parametrize("content", [None, "   ", '""'])
def test_translate_prompt_rejects_empty_result(tmp_path, content) -> None:
    with pytest.raises(PromptTranslationError, match="빈 번역"):
        translate_prompt(
            "고양이",
            make_settings(tmp_path),
            transport=openai_transport(chat_response(content)),
        )


def test_translate_prompt_rejects_malformed_response(tmp_path) -> None:
    with pytest.raises(PromptTranslationError, match="해석할 수 없습니다"):
        translate_prompt(
            "고양이",
            make_settings(tmp_path),
            transport=openai_transport(httpx.Response(200, json={"choices": []})),
        )


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ('A cafe with a neon sign that reads "OPEN"', 'A cafe with a neon sign that reads "OPEN"'),
        ('"Tokyo" written in neon above a street', '"Tokyo" written in neon above a street'),
        ("“A cat on a sofa.”", "A cat on a sofa."),
    ],
)
def test_translate_prompt_strips_only_wrapping_quote_pair(tmp_path, content, expected) -> None:
    translated = translate_prompt(
        "간판",
        make_settings(tmp_path),
        transport=openai_transport(chat_response(content)),
    )

    assert translated == expected
