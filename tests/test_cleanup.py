import os
from datetime import datetime, timedelta, timezone

from app.config import Settings
from app.services.cleanup import cleanup_runtime_files


def test_cleanup_runtime_files_removes_only_expired_files(tmp_path) -> None:
    upload_dir = tmp_path / "uploads"
    result_dir = tmp_path / "results"
    upload_dir.mkdir()
    result_dir.mkdir()

    expired_upload = upload_dir / "expired.txt"
    current_upload = upload_dir / "current.txt"
    expired_result = result_dir / "expired.pdf"
    expired_upload.write_text("old", encoding="utf-8")
    current_upload.write_text("new", encoding="utf-8")
    expired_result.write_bytes(b"old")

    expired_at = (datetime.now(timezone.utc) - timedelta(hours=25)).timestamp()
    os.utime(expired_upload, (expired_at, expired_at))
    os.utime(expired_result, (expired_at, expired_at))

    settings = Settings(
        upload_dir=upload_dir,
        result_dir=result_dir,
        max_upload_mb=1,
        upload_retention_hours=24,
        result_retention_hours=24,
        cleanup_interval_minutes=60,
        youtube_max_download_mb=500,
        youtube_max_duration_seconds=7200,
    )

    removed = cleanup_runtime_files(settings)

    assert removed == 2
    assert not expired_upload.exists()
    assert not expired_result.exists()
    assert current_upload.exists()
