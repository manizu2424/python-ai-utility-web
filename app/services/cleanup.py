from datetime import datetime, timedelta, timezone
from pathlib import Path


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
