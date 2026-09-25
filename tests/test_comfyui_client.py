import json

import httpx
import pytest

from app.config import Settings
from app.services.comfyui_client import (
    ComfyUIError,
    ComfyUITimeoutError,
    ComfyUIUnavailableError,
    build_workflow,
    generate_image,
    load_workflow_template,
)


PNG = b"\x89PNG\r\n\x1a\n" + b"fake-image"
DONE_HISTORY = {
    "abc": {
        "outputs": {
            "10": {
                "images": [
                    {"filename": "ComfyUI_temp_0001.png", "subfolder": "", "type": "temp"}
                ]
            }
        },
        "status": {"status_str": "success", "completed": True, "messages": []},
    }
}
ACCEPTED = {"prompt_id": "abc", "number": 1, "node_errors": {}}


def make_settings(
    tmp_path,
    comfyui_url: str | None = "http://comfy.test",
    timeout_seconds: int = 300,
) -> Settings:
    return Settings(
        upload_dir=tmp_path / "uploads",
        result_dir=tmp_path / "results",
        max_upload_mb=1,
        upload_retention_hours=24,
        result_retention_hours=24,
        cleanup_interval_minutes=60,
        youtube_max_download_mb=10,
        youtube_max_duration_seconds=7200,
        comfyui_url=comfyui_url,
        comfyui_timeout_seconds=timeout_seconds,
    )


def comfy_transport(
    histories: list[dict],
    *,
    prompt_response: httpx.Response | None = None,
    view_content: bytes = PNG,
    requests: list[httpx.Request] | None = None,
) -> httpx.MockTransport:
    history_iter = iter(histories)

    def handler(request: httpx.Request) -> httpx.Response:
        if requests is not None:
            requests.append(request)
        if request.method == "POST" and request.url.path == "/prompt":
            return prompt_response or httpx.Response(200, json=ACCEPTED)
        if request.url.path == "/history/abc":
            return httpx.Response(200, json=next(history_iter))
        if request.url.path == "/view":
            return httpx.Response(200, content=view_content)
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def test_workflow_template_has_expected_nodes() -> None:
    template = load_workflow_template()

    assert template["2"]["class_type"] == "CLIPTextEncode"
    assert template["5"]["class_type"] == "KSampler"
    assert template["8"]["class_type"] == "EmptySD3LatentImage"


def test_build_workflow_sets_values_without_mutating_template() -> None:
    workflow = build_workflow("a cat on a sofa", 1024, 768, 42)

    assert workflow["2"]["inputs"]["text"] == "a cat on a sofa"
    assert workflow["5"]["inputs"]["seed"] == 42
    assert workflow["8"]["inputs"]["width"] == 1024
    assert workflow["8"]["inputs"]["height"] == 768
    template = load_workflow_template()
    assert template["2"]["inputs"]["text"] == ""
    assert template["8"]["inputs"]["width"] == 768


def test_generate_image_returns_png_after_polling(tmp_path) -> None:
    requests: list[httpx.Request] = []
    sleeps: list[float] = []

    image = generate_image(
        "a cat on a sofa",
        "portrait",
        make_settings(tmp_path),
        transport=comfy_transport([{}, DONE_HISTORY], requests=requests),
        sleep=sleeps.append,
        clock=lambda: 0.0,
    )

    assert image.content == PNG
    assert (image.width, image.height) == (768, 1024)
    submitted = json.loads(requests[0].content)["prompt"]
    assert requests[0].url == "http://comfy.test/prompt"
    assert submitted["2"]["inputs"]["text"] == "a cat on a sofa"
    assert submitted["5"]["inputs"]["seed"] == image.seed
    assert sleeps == [2.0]
    view = requests[-1]
    assert view.url.path == "/view"
    assert view.url.params["filename"] == "ComfyUI_temp_0001.png"
    assert view.url.params["type"] == "temp"


def test_generate_image_requires_comfyui_url(tmp_path) -> None:
    with pytest.raises(ComfyUIUnavailableError, match="COMFYUI_URL"):
        generate_image("a cat", "square", make_settings(tmp_path, comfyui_url=None))


def test_generate_image_reports_unreachable_comfyui(tmp_path) -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(ComfyUIUnavailableError, match="연결할 수 없습니다"):
        generate_image(
            "a cat",
            "square",
            make_settings(tmp_path),
            transport=httpx.MockTransport(refuse),
        )


def test_generate_image_reports_node_errors(tmp_path) -> None:
    rejected = httpx.Response(
        400,
        json={
            "error": {
                "type": "prompt_outputs_failed_validation",
                "message": "Prompt outputs failed validation",
                "details": "",
            },
            "node_errors": {
                "1": {
                    "errors": [
                        {
                            "type": "value_not_in_list",
                            "message": "Value not in list",
                            "details": "unet_name: 'z-image-turbo-Q4_K_M.gguf' not in []",
                        }
                    ],
                    "class_type": "UnetLoaderGGUF",
                }
            },
        },
    )

    with pytest.raises(ComfyUIError) as exc_info:
        generate_image(
            "a cat",
            "square",
            make_settings(tmp_path),
            transport=comfy_transport([], prompt_response=rejected),
        )

    assert type(exc_info.value) is ComfyUIError
    assert "거부" in str(exc_info.value)
    assert "unet_name" in str(exc_info.value)


def test_generate_image_reports_missing_node_type(tmp_path) -> None:
    rejected = httpx.Response(
        400,
        json={
            "error": {
                "type": "invalid_prompt",
                "message": "Cannot execute because node UnetLoaderGGUF does not exist.",
                "details": "",
            },
            "node_errors": {},
        },
    )

    with pytest.raises(ComfyUIError, match="UnetLoaderGGUF does not exist"):
        generate_image(
            "a cat",
            "square",
            make_settings(tmp_path),
            transport=comfy_transport([], prompt_response=rejected),
        )


def test_generate_image_reports_non_json_prompt_response(tmp_path) -> None:
    html = httpx.Response(500, text="<html>Internal Server Error</html>")

    with pytest.raises(ComfyUIError) as exc_info:
        generate_image(
            "a cat",
            "square",
            make_settings(tmp_path),
            transport=comfy_transport([], prompt_response=html),
        )

    assert type(exc_info.value) is ComfyUIError
    assert "HTTP 500" in str(exc_info.value)


def test_generate_image_reports_execution_error(tmp_path) -> None:
    failed = {
        "abc": {
            "outputs": {},
            "status": {
                "status_str": "error",
                "completed": False,
                "messages": [
                    ["execution_start", {"prompt_id": "abc"}],
                    [
                        "execution_error",
                        {"prompt_id": "abc", "exception_message": "CUDA out of memory"},
                    ],
                ],
            },
        }
    }

    with pytest.raises(ComfyUIError, match="CUDA out of memory"):
        generate_image(
            "a cat",
            "square",
            make_settings(tmp_path),
            transport=comfy_transport([failed]),
            sleep=lambda seconds: None,
            clock=lambda: 0.0,
        )


def test_generate_image_times_out(tmp_path) -> None:
    clock = iter([0.0, 0.0, 301.0]).__next__

    with pytest.raises(ComfyUITimeoutError, match="시간"):
        generate_image(
            "a cat",
            "square",
            make_settings(tmp_path, timeout_seconds=300),
            transport=comfy_transport([{}, {}]),
            sleep=lambda seconds: None,
            clock=clock,
        )


def test_generate_image_rejects_history_without_images(tmp_path) -> None:
    no_images = {
        "abc": {
            "outputs": {"9": {}},
            "status": {"status_str": "success", "completed": True, "messages": []},
        }
    }

    with pytest.raises(ComfyUIError, match="이미지가 없습니다"):
        generate_image(
            "a cat",
            "square",
            make_settings(tmp_path),
            transport=comfy_transport([no_images]),
            sleep=lambda seconds: None,
            clock=lambda: 0.0,
        )


def test_generate_image_rejects_non_png_view(tmp_path) -> None:
    with pytest.raises(ComfyUIError, match="이미지를 받지 못했습니다"):
        generate_image(
            "a cat",
            "square",
            make_settings(tmp_path),
            transport=comfy_transport([DONE_HISTORY], view_content=b"<html>404</html>"),
            sleep=lambda seconds: None,
            clock=lambda: 0.0,
        )


def test_generate_image_reports_url_without_scheme(tmp_path) -> None:
    with pytest.raises(ComfyUIUnavailableError, match="http://"):
        generate_image("a cat", "square", make_settings(tmp_path, comfyui_url="100.64.0.2:8188"))
