from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.services.youtube_downloader import (
    YoutubeDownloadError,
    YoutubeDownloadResult,
    download_youtube,
    normalize_youtube_url,
)


def make_settings(tmp_path, max_download_mb: int = 10) -> Settings:
    return Settings(
        upload_dir=tmp_path / "uploads",
        result_dir=tmp_path / "results",
        max_upload_mb=1,
        upload_retention_hours=24,
        result_retention_hours=24,
        cleanup_interval_minutes=60,
        youtube_max_download_mb=max_download_mb,
        youtube_max_duration_seconds=7200,
    )


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "https://www.youtube.com/watch?v=abcdefghijk&list=ignored",
            "https://www.youtube.com/watch?v=abcdefghijk",
        ),
        (
            "https://youtu.be/abcdefghijk?t=10",
            "https://www.youtube.com/watch?v=abcdefghijk",
        ),
        (
            "https://www.youtube.com/shorts/abcdefghijk",
            "https://www.youtube.com/watch?v=abcdefghijk",
        ),
    ],
)
def test_normalize_youtube_url_accepts_single_video_urls(url: str, expected: str) -> None:
    assert normalize_youtube_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "http://www.youtube.com/watch?v=abcdefghijk",
        "https://youtube.com.example.com/watch?v=abcdefghijk",
        "https://www.youtube.com/playlist?list=abcdefghijk",
    ],
)
def test_normalize_youtube_url_rejects_unsafe_or_playlist_urls(url: str) -> None:
    with pytest.raises(YoutubeDownloadError):
        normalize_youtube_url(url)


def test_download_youtube_writes_video_result(tmp_path, monkeypatch) -> None:
    import yt_dlp

    settings = make_settings(tmp_path)
    captured: dict[str, object] = {}

    class FakeYoutubeDL:
        def __init__(self, options) -> None:
            captured["options"] = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            return None

        def extract_info(self, url: str, download: bool):
            captured["url"] = url
            captured["download"] = download
            output = Path(str(captured["options"]["outtmpl"]).replace("%(ext)s", "mp4"))
            output.write_bytes(b"video")
            return {"title": "Sample video", "duration": 65}

    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYoutubeDL)
    monkeypatch.setattr(
        "app.services.youtube_downloader.shutil.which",
        lambda command: f"/usr/bin/{command}",
    )

    result = download_youtube(
        "https://youtu.be/abcdefghijk",
        "video",
        settings,
    )

    assert captured["url"] == "https://www.youtube.com/watch?v=abcdefghijk"
    assert captured["download"] is True
    assert result.title == "Sample video"
    assert result.duration == 65
    assert result.extension == ".mp4"
    assert result.size == 5
    assert (settings.result_dir / f"{result.result_id}.mp4").exists()


def test_download_youtube_configures_mp3_extraction(tmp_path, monkeypatch) -> None:
    import yt_dlp

    settings = make_settings(tmp_path)
    captured: dict[str, object] = {}

    class FakeYoutubeDL:
        def __init__(self, options) -> None:
            captured["options"] = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            return None

        def extract_info(self, url: str, download: bool):
            options = captured["options"]
            output = Path(str(options["outtmpl"]).replace("%(ext)s", "mp3"))
            output.write_bytes(b"audio")
            return {"title": "Sample audio", "duration": 30}

    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYoutubeDL)
    monkeypatch.setattr(
        "app.services.youtube_downloader.shutil.which",
        lambda command: f"/usr/bin/{command}",
    )

    result = download_youtube(
        "https://youtu.be/abcdefghijk",
        "audio",
        settings,
    )

    options = captured["options"]
    assert options["format"] == "m4a/bestaudio/best"
    assert options["postprocessors"][0]["key"] == "FFmpegExtractAudio"
    assert options["postprocessors"][0]["preferredcodec"] == "mp3"
    assert result.extension == ".mp3"


def test_download_youtube_removes_partial_file_on_failure(tmp_path, monkeypatch) -> None:
    import yt_dlp
    from yt_dlp.utils import DownloadError

    settings = make_settings(tmp_path)

    class FailingYoutubeDL:
        def __init__(self, options) -> None:
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            return None

        def extract_info(self, url: str, download: bool):
            output = Path(self.options["outtmpl"].replace("%(ext)s", "mp4.part"))
            output.write_bytes(b"partial")
            raise DownloadError("download failed")

    monkeypatch.setattr(yt_dlp, "YoutubeDL", FailingYoutubeDL)
    monkeypatch.setattr(
        "app.services.youtube_downloader.shutil.which",
        lambda command: f"/usr/bin/{command}",
    )

    with pytest.raises(YoutubeDownloadError, match="다운로드에 실패"):
        download_youtube(
            "https://youtu.be/abcdefghijk",
            "video",
            settings,
        )

    assert list(settings.result_dir.iterdir()) == []


def test_download_youtube_rejects_unknown_mode(tmp_path) -> None:
    with pytest.raises(YoutubeDownloadError, match="영상 또는 음원"):
        download_youtube(
            "https://youtu.be/abcdefghijk",
            "subtitles",
            make_settings(tmp_path),
        )


def test_youtube_download_api_returns_result(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("RESULT_DIR", str(tmp_path / "results"))
    get_settings.cache_clear()

    def fake_download(url: str, mode: str, settings: Settings) -> YoutubeDownloadResult:
        assert url == "https://youtu.be/abcdefghijk"
        assert mode == "audio"
        settings.result_dir.mkdir(parents=True, exist_ok=True)
        (settings.result_dir / "result123.mp3").write_bytes(b"audio")
        return YoutubeDownloadResult(
            result_id="result123",
            title="Sample audio",
            duration=42,
            extension=".mp3",
            size=5,
            mode="audio",
        )

    monkeypatch.setattr("app.main.download_youtube", fake_download)
    with TestClient(app) as client:
        response = client.post(
            "/api/youtube/download",
            data={"url": "https://youtu.be/abcdefghijk", "mode": "audio"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["title"] == "Sample audio"
        assert payload["download_url"] == "/api/results/result123"

        download = client.get(payload["download_url"])
        assert download.status_code == 200
        assert download.headers["content-type"] == "audio/mpeg"
        assert download.content == b"audio"

    get_settings.cache_clear()
