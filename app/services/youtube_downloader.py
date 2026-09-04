import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from app.config import Settings
from app.services.storage import ensure_runtime_dirs


YOUTUBE_HOSTS = {
    "m.youtube.com",
    "music.youtube.com",
    "www.youtube.com",
    "www.youtube-nocookie.com",
    "youtu.be",
    "youtube.com",
    "youtube-nocookie.com",
}
VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{6,20}$")
DOWNLOAD_MODES = {"audio", "video"}


class YoutubeDownloadError(Exception):
    """Raised when a YouTube download cannot be completed safely."""


@dataclass(frozen=True)
class YoutubeDownloadResult:
    result_id: str
    title: str
    duration: int | None
    extension: str
    size: int
    mode: str


def normalize_youtube_url(url: str) -> str:
    """Validate a YouTube video URL and return a minimal canonical URL."""
    try:
        parsed = urlparse(url.strip())
        hostname = (parsed.hostname or "").lower()
        port = parsed.port
    except ValueError as exc:
        raise YoutubeDownloadError("올바른 유튜브 URL을 입력하세요.") from exc

    if (
        parsed.scheme != "https"
        or hostname not in YOUTUBE_HOSTS
        or parsed.username
        or parsed.password
        or port not in {None, 443}
    ):
        raise YoutubeDownloadError(
            "HTTPS 방식의 유튜브 영상 URL만 사용할 수 있습니다."
        )

    path_parts = [part for part in parsed.path.split("/") if part]
    video_id = ""

    if hostname == "youtu.be" and path_parts:
        video_id = path_parts[0]
    elif parsed.path == "/watch":
        video_id = parse_qs(parsed.query).get("v", [""])[0]
    elif len(path_parts) >= 2 and path_parts[0] in {"embed", "live", "shorts"}:
        video_id = path_parts[1]

    if not VIDEO_ID_PATTERN.fullmatch(video_id):
        raise YoutubeDownloadError(
            "재생 가능한 단일 유튜브 영상 URL을 입력하세요."
        )

    return f"https://www.youtube.com/watch?v={video_id}"


def download_youtube(
    url: str,
    mode: str,
    settings: Settings,
) -> YoutubeDownloadResult:
    """Download one YouTube video or its MP3 audio into the result directory."""
    if mode not in DOWNLOAD_MODES:
        raise YoutubeDownloadError(
            "다운로드 형식은 영상 또는 음원만 선택할 수 있습니다."
        )

    canonical_url = normalize_youtube_url(url)
    _require_ffmpeg()

    try:
        from yt_dlp import YoutubeDL
        from yt_dlp.utils import DownloadError
    except ImportError as exc:
        raise YoutubeDownloadError("yt-dlp가 설치되어 있지 않습니다.") from exc

    ensure_runtime_dirs(settings)
    result_id = uuid4().hex
    output_template = str(settings.result_dir / f"{result_id}.%(ext)s")
    options = _build_options(output_template, mode, settings)

    try:
        with YoutubeDL(options) as downloader:
            info = downloader.extract_info(canonical_url, download=True)
        if not info or not hasattr(info, "get"):
            raise YoutubeDownloadError("영상 정보를 확인할 수 없습니다.")
        result_path = _select_result_file(settings.result_dir, result_id, mode)
        size = result_path.stat().st_size
        if size > settings.youtube_max_download_bytes:
            raise YoutubeDownloadError(
                "다운로드 결과는 "
                f"{settings.youtube_max_download_mb}MB 이하만 허용됩니다."
            )
    except YoutubeDownloadError:
        _remove_download_files(settings.result_dir, result_id)
        raise
    except DownloadError as exc:
        _remove_download_files(settings.result_dir, result_id)
        raise YoutubeDownloadError(
            "유튜브 다운로드에 실패했습니다. "
            "URL, 공개 범위 또는 영상 상태를 확인하세요."
        ) from exc
    except Exception as exc:
        _remove_download_files(settings.result_dir, result_id)
        raise YoutubeDownloadError(
            "유튜브 다운로드 처리 중 오류가 발생했습니다."
        ) from exc

    title = str(info.get("title") or "YouTube download")
    raw_duration = info.get("duration")
    duration = int(raw_duration) if isinstance(raw_duration, (int, float)) else None
    return YoutubeDownloadResult(
        result_id=result_id,
        title=title,
        duration=duration,
        extension=result_path.suffix.lower(),
        size=size,
        mode=mode,
    )


def _build_options(
    output_template: str,
    mode: str,
    settings: Settings,
) -> dict[str, Any]:
    def duration_filter(info: dict[str, Any], *, incomplete: bool) -> str | None:
        del incomplete
        duration = info.get("duration")
        if duration and duration > settings.youtube_max_duration_seconds:
            return (
                "영상 길이가 허용 범위를 초과했습니다. "
                f"최대 {settings.youtube_max_duration_seconds}초"
            )
        return None

    options: dict[str, Any] = {
        "cachedir": False,
        "fragment_retries": 3,
        "ignoreconfig": True,
        "match_filter": duration_filter,
        "max_filesize": settings.youtube_max_download_bytes,
        "noplaylist": True,
        "no_warnings": True,
        "outtmpl": output_template,
        "overwrites": False,
        "quiet": True,
        "retries": 3,
        "socket_timeout": 30,
    }

    if mode == "audio":
        options.update(
            {
                "format": "m4a/bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }
        )
    else:
        options.update(
            {
                "format": (
                    "bv*[ext=mp4][height<=1080]+ba[ext=m4a]/"
                    "b[ext=mp4][height<=1080]/best[height<=1080]"
                ),
                "merge_output_format": "mp4",
            }
        )

    return options


def _require_ffmpeg() -> None:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise YoutubeDownloadError("ffmpeg와 ffprobe 실행 파일이 필요합니다.")


def _select_result_file(result_dir: Path, result_id: str, mode: str) -> Path:
    excluded_extensions = {".description", ".json", ".part", ".vtt", ".ytdl"}
    candidates = [
        path
        for path in result_dir.glob(f"{result_id}.*")
        if path.is_file() and path.suffix.lower() not in excluded_extensions
    ]
    if not candidates:
        raise YoutubeDownloadError("다운로드 결과 파일을 찾을 수 없습니다.")

    preferred = {"audio": {".mp3"}, "video": {".mkv", ".mp4", ".webm"}}[mode]
    candidates.sort(
        key=lambda path: (
            path.suffix.lower() in preferred,
            path.stat().st_mtime,
            path.stat().st_size,
        ),
        reverse=True,
    )
    selected = candidates[0]
    for path in candidates[1:]:
        path.unlink(missing_ok=True)
    return selected


def _remove_download_files(result_dir: Path, result_id: str) -> None:
    for path in result_dir.glob(f"{result_id}.*"):
        if path.is_file():
            path.unlink(missing_ok=True)
