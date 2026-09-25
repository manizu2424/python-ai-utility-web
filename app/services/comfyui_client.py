import json
import random
import time
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings


WORKFLOW_PATH = (
    Path(__file__).resolve().parent.parent / "comfyui_workflows" / "z_image_turbo.json"
)
# Node ids in z_image_turbo.json (ComfyUI API format); update together with the template.
PROMPT_NODE = "2"
SAMPLER_NODE = "5"
LATENT_NODE = "8"
IMAGE_SIZES = {
    "portrait": (768, 1024),
    "landscape": (1024, 768),
    "square": (1024, 1024),
}
# ComfyUI API does not apply the UI's "randomize" seed control, so the server picks one.
MAX_SEED = 2**53 - 1
POLL_INTERVAL_SECONDS = 2.0
REQUEST_TIMEOUT_SECONDS = 30.0
MAX_ERROR_CHARS = 300
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
UNREACHABLE_MESSAGE = (
    "Windows PC의 ComfyUI에 연결할 수 없습니다. "
    "PC 전원, ComfyUI --listen 실행, Tailscale 연결을 확인하세요."
)


class ComfyUIError(Exception):
    """Raised when ComfyUI rejects or fails a generation job."""


class ComfyUIUnavailableError(ComfyUIError):
    """Raised when ComfyUI is not configured or cannot be reached."""


class ComfyUITimeoutError(ComfyUIError):
    """Raised when a job does not finish within the configured wait."""


@dataclass(frozen=True)
class GeneratedImage:
    content: bytes
    seed: int
    width: int
    height: int


@lru_cache
def load_workflow_template() -> dict[str, Any]:
    return json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))


def build_workflow(prompt: str, width: int, height: int, seed: int) -> dict[str, Any]:
    workflow = deepcopy(load_workflow_template())
    workflow[PROMPT_NODE]["inputs"]["text"] = prompt
    workflow[SAMPLER_NODE]["inputs"]["seed"] = seed
    workflow[LATENT_NODE]["inputs"]["width"] = width
    workflow[LATENT_NODE]["inputs"]["height"] = height
    return workflow


def generate_image(
    prompt: str,
    size: str,
    settings: Settings,
    *,
    transport: httpx.BaseTransport | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> GeneratedImage:
    if not settings.comfyui_url:
        raise ComfyUIUnavailableError("서버에 COMFYUI_URL이 설정되지 않았습니다.")

    width, height = IMAGE_SIZES[size]
    seed = random.randint(0, MAX_SEED)
    workflow = build_workflow(prompt, width, height, seed)

    try:
        with httpx.Client(
            base_url=settings.comfyui_url,
            transport=transport,
            timeout=REQUEST_TIMEOUT_SECONDS,
        ) as client:
            prompt_id = _submit(client, workflow)
            image_ref = _wait_for_image(
                client,
                prompt_id,
                settings.comfyui_timeout_seconds,
                sleep,
                clock,
            )
            content = _download(client, image_ref)
    except httpx.UnsupportedProtocol as exc:
        raise ComfyUIUnavailableError(
            "COMFYUI_URL은 http://로 시작해야 합니다(예: http://<windows-tailscale-ip>:8188)."
        ) from exc
    except httpx.TransportError as exc:
        raise ComfyUIUnavailableError(UNREACHABLE_MESSAGE) from exc

    return GeneratedImage(content=content, seed=seed, width=width, height=height)


def _submit(client: httpx.Client, workflow: dict[str, Any]) -> str:
    response = client.post("/prompt", json={"prompt": workflow})
    payload = _json_object(response)
    if response.status_code == 400 or payload.get("node_errors"):
        raise ComfyUIError(f"ComfyUI가 작업을 거부했습니다: {_describe_rejection(payload)}")
    prompt_id = payload.get("prompt_id")
    if response.is_error or not isinstance(prompt_id, str):
        raise ComfyUIError(
            f"ComfyUI 작업 제출에 실패했습니다(HTTP {response.status_code})."
        )
    return prompt_id


def _wait_for_image(
    client: httpx.Client,
    prompt_id: str,
    timeout_seconds: int,
    sleep: Callable[[float], None],
    clock: Callable[[], float],
) -> dict[str, str]:
    deadline = clock() + timeout_seconds
    while True:
        response = client.get(f"/history/{prompt_id}")
        if response.is_error:
            raise ComfyUIError(
                f"ComfyUI 작업 상태를 확인하지 못했습니다(HTTP {response.status_code})."
            )
        # History stays empty while the job is queued or running.
        entry = _json_object(response).get(prompt_id)
        if isinstance(entry, dict):
            return _extract_image(entry)
        if clock() >= deadline:
            raise ComfyUITimeoutError(
                f"{timeout_seconds}초 안에 생성이 끝나지 않아 대기 시간을 초과했습니다. "
                "Windows ComfyUI 대기열에 작업이 남아 있을 수 있습니다."
            )
        sleep(POLL_INTERVAL_SECONDS)


def _extract_image(entry: dict[str, Any]) -> dict[str, str]:
    status = entry.get("status") or {}
    if status.get("status_str") == "error":
        raise ComfyUIError(
            f"ComfyUI 실행 중 오류가 발생했습니다: {_describe_execution_error(status)}"
        )

    for output in (entry.get("outputs") or {}).values():
        for image in output.get("images") or []:
            if image.get("filename"):
                return {
                    "filename": image["filename"],
                    "subfolder": image.get("subfolder", ""),
                    "type": image.get("type", "output"),
                }
    raise ComfyUIError("ComfyUI 결과에 이미지가 없습니다. 워크플로 출력 노드를 확인하세요.")


def _download(client: httpx.Client, image_ref: dict[str, str]) -> bytes:
    response = client.get("/view", params=image_ref)
    if response.is_error or not response.content.startswith(PNG_SIGNATURE):
        raise ComfyUIError("ComfyUI에서 생성 이미지를 받지 못했습니다.")
    return response.content


def _json_object(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _describe_rejection(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    error = payload.get("error")
    if isinstance(error, dict) and error.get("message"):
        parts.append(str(error["message"]))
    for node_id, node_error in (payload.get("node_errors") or {}).items():
        for item in node_error.get("errors") or []:
            detail = f"{item.get('message', '')} {item.get('details', '')}".strip()
            parts.append(f"노드 {node_id}: {detail}")
    return _truncate(" / ".join(parts) or "알 수 없는 오류")


def _describe_execution_error(status: dict[str, Any]) -> str:
    for message in status.get("messages") or []:
        if (
            isinstance(message, list)
            and len(message) == 2
            and message[0] == "execution_error"
            and isinstance(message[1], dict)
        ):
            text = str(message[1].get("exception_message", "")).strip()
            if text:
                return _truncate(text)
    return "알 수 없는 오류"


def _truncate(text: str) -> str:
    if len(text) <= MAX_ERROR_CHARS:
        return text
    return text[: MAX_ERROR_CHARS - 1] + "…"
