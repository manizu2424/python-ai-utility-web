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
