import asyncio
import os
from datetime import datetime, timedelta, timezone
from threading import get_ident

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.services import cleanup
from app.services.cleanup import cleanup_runtime_files


def make_settings(tmp_path, cleanup_interval_minutes: int = 60) -> Settings:
    return Settings(
        upload_dir=tmp_path / "uploads",
        result_dir=tmp_path / "results",
        max_upload_mb=1,
        upload_retention_hours=24,
        result_retention_hours=24,
        cleanup_interval_minutes=cleanup_interval_minutes,
        youtube_max_download_mb=500,
        youtube_max_duration_seconds=7200,
    )


def make_expired(path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("old", encoding="utf-8")
    expired_at = (datetime.now(timezone.utc) - timedelta(hours=25)).timestamp()
    os.utime(path, (expired_at, expired_at))


def test_cleanup_runtime_files_removes_only_expired_files(tmp_path) -> None:
    settings = make_settings(tmp_path)
    expired_upload = settings.upload_dir / "expired.txt"
    expired_result = settings.result_dir / "expired.pdf"
    current_upload = settings.upload_dir / "current.txt"
    make_expired(expired_upload)
    make_expired(expired_result)
    current_upload.write_text("new", encoding="utf-8")

    removed = cleanup_runtime_files(settings)

    assert removed == 2
    assert not expired_upload.exists()
    assert not expired_result.exists()
    assert current_upload.exists()


@pytest.mark.parametrize(
    ("interval_minutes", "expected_seconds"),
    [(5, 300), (0, 60)],
)
def test_run_cleanup_loop_cleans_each_interval_in_worker_thread(
    tmp_path,
    monkeypatch,
    interval_minutes: int,
    expected_seconds: int,
) -> None:
    settings = make_settings(tmp_path, cleanup_interval_minutes=interval_minutes)
    sleeps: list[float] = []
    cleanup_thread_ids: list[int] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        if len(sleeps) == 3:
            raise asyncio.CancelledError

    def fake_cleanup(received: Settings) -> int:
        assert received is settings
        cleanup_thread_ids.append(get_ident())
        return 0

    monkeypatch.setattr(cleanup.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(cleanup, "cleanup_runtime_files", fake_cleanup)

    async def run_loop() -> int:
        event_loop_thread_id = get_ident()
        with pytest.raises(asyncio.CancelledError):
            await cleanup.run_cleanup_loop(settings)
        return event_loop_thread_id

    event_loop_thread_id = asyncio.run(run_loop())

    assert sleeps == [expected_seconds] * 3
    assert len(cleanup_thread_ids) == 2
    assert event_loop_thread_id not in cleanup_thread_ids


def test_app_startup_removes_expired_files(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("RESULT_DIR", str(tmp_path / "results"))
    get_settings.cache_clear()
    expired_upload = tmp_path / "uploads" / "expired.txt"
    make_expired(expired_upload)

    try:
        with TestClient(app):
            assert not expired_upload.exists()
    finally:
        get_settings.cache_clear()
