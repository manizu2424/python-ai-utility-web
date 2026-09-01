import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

SUPPORTED_TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".pdf",
    ".docx",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}

SUPPORTED_PDF_EXTENSIONS = {".pdf"}

SUPPORTED_TO_PDF_EXTENSIONS = {
    ".txt",
    ".md",
    ".docx",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}


@dataclass(frozen=True)
class Settings:
    upload_dir: Path
    result_dir: Path
    max_upload_mb: int
    upload_retention_hours: int
    result_retention_hours: int

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings(
        upload_dir=Path(os.getenv("UPLOAD_DIR", BASE_DIR / "uploads")),
        result_dir=Path(os.getenv("RESULT_DIR", BASE_DIR / "results")),
        max_upload_mb=int(os.getenv("MAX_UPLOAD_MB", "100")),
        upload_retention_hours=int(os.getenv("UPLOAD_RETENTION_HOURS", "24")),
        result_retention_hours=int(os.getenv("RESULT_RETENTION_HOURS", "24")),
    )
