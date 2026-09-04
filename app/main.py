import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.routers import pdf, results, text, youtube
from app.services.cleanup import cleanup_runtime_files, run_cleanup_loop


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    await run_in_threadpool(cleanup_runtime_files, settings)
    cleanup_task = asyncio.create_task(run_cleanup_loop(settings))
    try:
        yield
    finally:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task


app = FastAPI(title="AI Utility Toolbox", lifespan=lifespan)
app.include_router(text.router)
app.include_router(pdf.router)
app.include_router(youtube.router)
app.include_router(results.router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
