from app.config import get_settings


def test_get_settings_reads_youtube_proxy(monkeypatch) -> None:
    monkeypatch.setenv("YOUTUBE_PROXY", "socks5://100.64.0.1:1080")
    get_settings.cache_clear()
    try:
        assert get_settings().youtube_proxy == "socks5://100.64.0.1:1080"
    finally:
        get_settings.cache_clear()


def test_get_settings_treats_blank_youtube_proxy_as_direct(monkeypatch) -> None:
    monkeypatch.setenv("YOUTUBE_PROXY", "  ")
    get_settings.cache_clear()
    try:
        assert get_settings().youtube_proxy is None
    finally:
        get_settings.cache_clear()


def test_get_settings_reads_image_generation_settings(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", " sk-test ")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    monkeypatch.setenv("COMFYUI_URL", "http://100.64.0.2:8188/")
    monkeypatch.setenv("COMFYUI_TIMEOUT_SECONDS", "120")
    get_settings.cache_clear()
    try:
        settings = get_settings()
        assert settings.openai_api_key == "sk-test"
        assert settings.openai_model == "gpt-test"
        assert settings.comfyui_url == "http://100.64.0.2:8188"
        assert settings.comfyui_timeout_seconds == 120
    finally:
        get_settings.cache_clear()


def test_get_settings_image_generation_defaults(monkeypatch) -> None:
    for name in (
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "COMFYUI_URL",
        "COMFYUI_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OPENAI_MODEL", "  ")
    get_settings.cache_clear()
    try:
        settings = get_settings()
        assert settings.openai_api_key is None
        assert settings.openai_model == "gpt-6-luna"
        assert settings.comfyui_url is None
        assert settings.comfyui_timeout_seconds == 300
    finally:
        get_settings.cache_clear()
