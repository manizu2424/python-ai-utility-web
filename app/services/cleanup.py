import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.config import Settings


def remove_expired_files(directory: Path, retention_hours: int) -> int:
    if not directory.exists():
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
    removed = 0

    for path in directory.iterdir():
        if not path.is_file():
            continue
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        if modified < cutoff:
            path.unlink()
            removed += 1

    return removed


def cleanup_runtime_files(settings: Settings) -> int:
    """Remove expired uploads and generated results."""
    return remove_expired_files(
        settings.upload_dir,
        settings.upload_retention_hours,
    ) + remove_expired_files(
        settings.result_dir,
        settings.result_retention_hours,
    )


async def run_cleanup_loop(settings: Settings) -> None:
    """Periodically clean runtime files while the application is running."""
    interval_seconds = max(settings.cleanup_interval_minutes, 1) * 60

    while True:
        await asyncio.sleep(interval_seconds)
        await asyncio.to_thread(cleanup_runtime_files, settings)
