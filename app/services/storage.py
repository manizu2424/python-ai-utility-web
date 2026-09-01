from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.config import SUPPORTED_TEXT_EXTENSIONS, Settings


@dataclass(frozen=True)
class StoredFile:
    original_filename: str
    path: Path
    extension: str
    size: int


def ensure_runtime_dirs(settings: Settings) -> None:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.result_dir.mkdir(parents=True, exist_ok=True)


MEDIA_TYPES = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pdf": "application/pdf",
    ".txt": "text/plain; charset=utf-8",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".zip": "application/zip",
}


@dataclass(frozen=True)
class ResultFile:
    path: Path
    media_type: str
    filename: str


def validate_extension(
    filename: str,
    allowed_extensions: set[str] | None = None,
) -> str:
    allowed = allowed_extensions or SUPPORTED_TEXT_EXTENSIONS
    extension = Path(filename).suffix.lower()
    if not extension or extension not in allowed:
        supported = ", ".join(sorted(allowed))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {supported}",
        )
    return extension


async def save_upload(
    upload: UploadFile,
    settings: Settings,
    allowed_extensions: set[str] | None = None,
) -> StoredFile:
    if not upload.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="파일 이름이 없습니다.",
        )

    ensure_runtime_dirs(settings)
    extension = validate_extension(upload.filename, allowed_extensions)
    stored_path = settings.upload_dir / f"{uuid4().hex}{extension}"
    size = 0

    try:
        with stored_path.open("wb") as output:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"파일 크기는 {settings.max_upload_mb}MB 이하만 허용됩니다.",
                    )
                output.write(chunk)
    except HTTPException:
        stored_path.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()

    if size == 0:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="빈 파일은 처리할 수 없습니다.",
        )

    return StoredFile(
        original_filename=Path(upload.filename).name,
        path=stored_path,
        extension=extension,
        size=size,
    )


def save_text_result(text: str, settings: Settings) -> str:
    return save_result_bytes(text.encode("utf-8"), ".txt", settings)


def save_result_bytes(content: bytes, extension: str, settings: Settings) -> str:
    ensure_runtime_dirs(settings)
    result_id = uuid4().hex
    result_path = settings.result_dir / f"{result_id}{extension}"
    result_path.write_bytes(content)
    return result_id


def get_result_file(result_id: str, settings: Settings) -> ResultFile:
    if not result_id.isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="잘못된 결과 파일 ID입니다.",
        )

    matches = list(settings.result_dir.glob(f"{result_id}.*"))
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="결과 파일을 찾을 수 없습니다.",
        )

    result_path = matches[0]
    extension = result_path.suffix.lower()
    return ResultFile(
        path=result_path,
        media_type=MEDIA_TYPES.get(extension, "application/octet-stream"),
        filename=result_path.name,
    )
