from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.services.youtube_transcript import (
    YoutubeTranscriptResult,
    YoutubeTranscriptError,
    extract_youtube_transcript,
    parse_vtt,
)
from tests.test_youtube_downloader import make_settings


def test_parse_vtt_removes_markup_and_rolling_duplicates() -> None:
    content = """WEBVTT

00:00:00.000 --> 00:00:01.000
<c>Hello</c>

00:00:01.000 --> 00:00:02.000
<c>Hello world</c>

00:00:02.000 --> 00:00:03.000
Again &amp; again
"""

    assert parse_vtt(content) == "Hello world Again & again"


def test_extract_youtube_transcript_uses_korean_caption(tmp_path, monkeypatch) -> None:
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
            subtitle = Path(
                str(options["outtmpl"]).replace(".%(ext)s", ".ko.vtt")
            )
            subtitle.write_text(
                "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\n안녕하세요\n",
                encoding="utf-8",
            )
            captured["url"] = url
            captured["download"] = download
            return {"title": "한국어 영상", "duration": 20}

    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYoutubeDL)

    result = extract_youtube_transcript(
        "https://youtu.be/abcdefghijk",
        "auto",
        settings,
    )

    options = captured["options"]
    assert options["skip_download"] is True
    assert options["writeautomaticsub"] is True
    assert options["writesubtitles"] is True
    assert captured["url"] == "https://www.youtube.com/watch?v=abcdefghijk"
    assert result.title == "한국어 영상"
    assert result.language == "ko"
    assert result.text == "안녕하세요"
    assert list(settings.upload_dir.iterdir()) == []


def test_extract_youtube_transcript_reports_missing_captions(tmp_path, monkeypatch) -> None:
    import yt_dlp

    settings = make_settings(tmp_path)

    class FakeYoutubeDL:
        def __init__(self, options) -> None:
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            return None

        def extract_info(self, url: str, download: bool):
            return {"title": "No captions", "duration": 20}

    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYoutubeDL)

    with pytest.raises(YoutubeTranscriptError, match="자막이 없습니다"):
        extract_youtube_transcript(
            "https://youtu.be/abcdefghijk",
            "ko",
            settings,
        )


def test_youtube_transcript_api_returns_downloadable_text(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("RESULT_DIR", str(tmp_path / "results"))
    get_settings.cache_clear()

    def fake_transcript(
        url: str,
        language: str,
        settings: Settings,
    ) -> YoutubeTranscriptResult:
        assert language == "auto"
        return YoutubeTranscriptResult(
            title="Sample video",
            duration=30,
            language="ko",
            source_url="https://www.youtube.com/watch?v=abcdefghijk",
            text="추출한 자막",
        )

    monkeypatch.setattr("app.main.extract_youtube_transcript", fake_transcript)
    with TestClient(app) as client:
        response = client.post(
            "/api/youtube/transcript",
            data={"url": "https://youtu.be/abcdefghijk", "language": "auto"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["text"] == "추출한 자막"
        assert payload["language"] == "ko"
        download = client.get(payload["download_url"])
        assert download.status_code == 200
        assert download.text == "추출한 자막"

    get_settings.cache_clear()
