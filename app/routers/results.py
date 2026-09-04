from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.config import get_settings
from app.services.storage import get_result_file


router = APIRouter(prefix="/api/results")


@router.get("/{result_id}")
def download_result(result_id: str) -> FileResponse:
    result_file = get_result_file(result_id, get_settings())
    return FileResponse(
        result_file.path,
        media_type=result_file.media_type,
        filename=result_file.filename,
    )
