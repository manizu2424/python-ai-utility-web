import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.services.comfyui_client import (
    ComfyUIError,
    ComfyUITimeoutError,
    ComfyUIUnavailableError,
    GeneratedImage,
)
from app.services.prompt_translator import (
    PromptTranslationError,
    TranslationUnavailableError,
)


PNG = b"\x89PNG\r\n\x1a\n" + b"fake-image"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("RESULT_DIR", str(tmp_path / "results"))
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


def test_translate_endpoint_returns_english_prompt(client, monkeypatch) -> None:
    def fake_translate(text: str, settings: Settings) -> str:
        assert text == "소파 위의 고양이"
        return "A cat on a sofa."

    monkeypatch.setattr("app.routers.image.translate_prompt", fake_translate)

    response = client.post("/api/image/translate", data={"prompt": "  소파 위의 고양이 "})

    assert response.status_code == 200
    assert response.json() == {"prompt_en": "A cat on a sofa."}


@pytest.mark.parametrize("endpoint", ["/api/image/translate", "/api/image/generate"])
@pytest.mark.parametrize(
    ("prompt", "expected"),
    [("", "프롬프트를 입력하세요."), ("   ", "프롬프트를 입력하세요."), ("a" * 2001, "2000자")],
)
def test_endpoints_reject_blank_or_long_prompt(client, endpoint, prompt, expected) -> None:
    response = client.post(endpoint, data={"prompt": prompt})

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)
    assert expected in response.json()["detail"]


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (TranslationUnavailableError("서버에 OPENAI_API_KEY가 설정되지 않았습니다."), 503),
        (PromptTranslationError("OpenAI API 키가 올바르지 않습니다."), 502),
    ],
)
def test_translate_endpoint_maps_errors(client, monkeypatch, error, status_code) -> None:
    def fake_translate(text: str, settings: Settings) -> str:
        raise error

    monkeypatch.setattr("app.routers.image.translate_prompt", fake_translate)

    response = client.post("/api/image/translate", data={"prompt": "고양이"})

    assert response.status_code == status_code
    assert response.json()["detail"] == str(error)


def test_generate_endpoint_saves_png_and_serves_it(client, monkeypatch) -> None:
    def fake_generate(prompt: str, size: str, settings: Settings) -> GeneratedImage:
        assert prompt == "A cat on a sofa."
        assert size == "landscape"
        return GeneratedImage(content=PNG, seed=42, width=1024, height=768)

    monkeypatch.setattr("app.routers.image.generate_image", fake_generate)

    response = client.post(
        "/api/image/generate",
        data={"prompt": "A cat on a sofa.", "size": "landscape"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["seed"] == 42
    assert (payload["width"], payload["height"]) == (1024, 768)
    assert payload["download_url"] == f"/api/results/{payload['result_id']}"

    download = client.get(payload["download_url"])
    assert download.status_code == 200
    assert download.headers["content-type"] == "image/png"
    assert download.content == PNG


def test_generate_endpoint_rejects_unknown_size(client) -> None:
    response = client.post("/api/image/generate", data={"prompt": "a cat", "size": "huge"})

    assert response.status_code == 422
    assert "크기" in response.json()["detail"]


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (ComfyUIUnavailableError("Windows PC의 ComfyUI에 연결할 수 없습니다."), 503),
        (ComfyUITimeoutError("대기 시간을 초과했습니다."), 504),
        (ComfyUIError("ComfyUI가 작업을 거부했습니다: 노드 1"), 502),
    ],
)
def test_generate_endpoint_maps_errors(client, monkeypatch, error, status_code) -> None:
    def fake_generate(prompt: str, size: str, settings: Settings) -> GeneratedImage:
        raise error

    monkeypatch.setattr("app.routers.image.generate_image", fake_generate)

    response = client.post("/api/image/generate", data={"prompt": "a cat"})

    assert response.status_code == status_code
    assert response.json()["detail"] == str(error)
