import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config import Settings
from app.services.storage import ensure_runtime_dirs
from app.services.youtube_downloader import YoutubeDownloadError, normalize_youtube_url


TRANSCRIPT_LANGUAGES = {
    "auto": ["ko.*", "en.*"],
    "en": ["en.*"],
    "ko": ["ko.*"],
}
VTT_TAG_PATTERN = re.compile(r"<[^>]+>")
WHITESPACE_PATTERN = re.compile(r"\s+")


class YoutubeTranscriptError(Exception):
    """Raised when YouTube subtitles cannot be extracted."""


@dataclass(frozen=True)
class YoutubeTranscriptResult:
    title: str
    duration: int | None
    language: str
    source_url: str
    text: str


def extract_youtube_transcript(
    url: str,
    language: str,
    settings: Settings,
) -> YoutubeTranscriptResult:
    """Download preferred subtitles without downloading the media file."""
    if language not in TRANSCRIPT_LANGUAGES:
        raise YoutubeTranscriptError(
            "자막 언어는 자동, 한국어 또는 영어만 선택할 수 있습니다."
        )

    try:
        canonical_url = normalize_youtube_url(url)
    except YoutubeDownloadError as exc:
        raise YoutubeTranscriptError(str(exc)) from exc

    try:
        from yt_dlp import YoutubeDL
        from yt_dlp.utils import DownloadError
    except ImportError as exc:
        raise YoutubeTranscriptError("yt-dlp가 설치되어 있지 않습니다.") from exc

    ensure_runtime_dirs(settings)
    temporary_id = uuid4().hex
    output_template = str(settings.upload_dir / f"{temporary_id}.%(ext)s")
    options: dict[str, Any] = {
        "cachedir": False,
        "ignoreconfig": True,
        "noplaylist": True,
        "no_warnings": True,
        "outtmpl": output_template,
        "quiet": True,
        "retries": 3,
        "skip_download": True,
        "socket_timeout": 30,
        "subtitlesformat": "vtt",
        "subtitleslangs": TRANSCRIPT_LANGUAGES[language],
        "writeautomaticsub": True,
        "writesubtitles": True,
    }

    try:
        with YoutubeDL(options) as downloader:
            info = downloader.extract_info(canonical_url, download=True)
        if not info or not hasattr(info, "get"):
            raise YoutubeTranscriptError("영상 정보를 확인할 수 없습니다.")

        raw_duration = info.get("duration")
        duration = int(raw_duration) if isinstance(raw_duration, (int, float)) else None
        if duration and duration > settings.youtube_max_duration_seconds:
            raise YoutubeTranscriptError(
                "영상 길이가 허용 범위를 초과했습니다. "
                f"최대 {settings.youtube_max_duration_seconds}초"
            )

        subtitle_path, subtitle_language = _select_subtitle_file(
            settings.upload_dir,
            temporary_id,
            language,
        )
        text = parse_vtt(subtitle_path.read_text(encoding="utf-8", errors="replace"))
        if not text:
            raise YoutubeTranscriptError("자막에서 텍스트를 추출하지 못했습니다.")

        return YoutubeTranscriptResult(
            title=str(info.get("title") or "YouTube transcript"),
            duration=duration,
            language=subtitle_language,
            source_url=canonical_url,
            text=text,
        )
    except YoutubeTranscriptError:
        raise
    except DownloadError as exc:
        raise YoutubeTranscriptError(
            "유튜브 자막을 가져오지 못했습니다. "
            "자막 제공 여부를 확인하세요."
        ) from exc
    except Exception as exc:
        raise YoutubeTranscriptError(
            "유튜브 자막 처리 중 오류가 발생했습니다."
        ) from exc
    finally:
        _remove_transcript_files(settings.upload_dir, temporary_id)


def parse_vtt(content: str) -> str:
    """Convert WebVTT cues to readable text and remove rolling duplicates."""
    cues: list[str] = []
    previous = ""

    for block in re.split(r"(?:\r?\n){2,}", content):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timestamp_index = next(
            (index for index, line in enumerate(lines) if "-->" in line),
            None,
        )
        if timestamp_index is None:
            continue

        cue_lines = lines[timestamp_index + 1 :]
        cleaned_lines = []
        for line in cue_lines:
            cleaned = html.unescape(VTT_TAG_PATTERN.sub("", line))
            cleaned = WHITESPACE_PATTERN.sub(" ", cleaned).strip()
            if cleaned and (not cleaned_lines or cleaned != cleaned_lines[-1]):
                cleaned_lines.append(cleaned)

        cue = " ".join(cleaned_lines).strip()
        if not cue or cue == previous:
            continue
        if previous and cue.startswith(f"{previous} "):
            cue = cue[len(previous) :].strip()
        if cue:
            cues.append(cue)
        previous = " ".join(cleaned_lines).strip()

    return " ".join(cues).strip()


def _select_subtitle_file(
    upload_dir: Path,
    temporary_id: str,
    requested_language: str,
) -> tuple[Path, str]:
    candidates = list(upload_dir.glob(f"{temporary_id}.*.vtt"))
    if not candidates:
        raise YoutubeTranscriptError(
            "사용 가능한 한국어 또는 영어 자막이 없습니다."
        )

    def language_for(path: Path) -> str:
        return path.name[len(temporary_id) + 1 : -len(".vtt")]

    def score(path: Path) -> tuple[int, float]:
        language = language_for(path).lower()
        if requested_language == "auto":
            if language == "ko":
                preference = 4
            elif language.startswith("ko"):
                preference = 3
            elif language == "en":
                preference = 2
            else:
                preference = 1
        else:
            preference = 2 if language == requested_language else 1
        return preference, path.stat().st_mtime

    selected = max(candidates, key=score)
    return selected, language_for(selected)


def _remove_transcript_files(upload_dir: Path, temporary_id: str) -> None:
    for path in upload_dir.glob(f"{temporary_id}.*"):
        if path.is_file():
            path.unlink(missing_ok=True)
