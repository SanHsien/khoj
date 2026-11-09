"""Offline contract between khoj's Gemini adapters and the pinned google-genai SDK.

Why this exists: Dependabot bumps `google-genai` and the maintenance gate stays green
without touching the code that calls it. 2.x removed Imagen from the Gemini Developer
API (`generate_images` raises there), which no other check noticed.

How: AST-load the unchanged product function bodies (no Django/torch import) and replace
only the HTTP transport, so request serialization and response parsing run through the
actual SDK. Retry wrappers, credential loading, tracing and billing are out of scope.
No real credentials or model calls: external sockets are denied.

The SDK version is khoj's own pin (`pyproject.toml`), checked below. In the gate and CI
`KHOJ_REQUIRE_GENAI_CONTRACT=1`, so a missing SDK is a failure, never a skip; other
environments may skip. `tools/install_contract_deps.py` installs the pinned set.
"""

import ast
import asyncio
import base64
import importlib
import io
import json
import logging
import os
import re
import socket
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from typing import Any

import pytest

REQUIRED = os.environ.get("KHOJ_REQUIRE_GENAI_CONTRACT") == "1"


def need(module):
    """Import a module; a missing one fails when the contract is required, else skips."""
    if REQUIRED:
        return importlib.import_module(module)
    return pytest.importorskip(module, reason="Product SDK is not part of this environment")


genai = need("google.genai")
httpx = need("httpx")
gtypes = need("google.genai.types")
Image = need("PIL.Image")
_credentials = need("google.auth.credentials")
AnonymousCredentials, Credentials = _credentials.AnonymousCredentials, _credentials.Credentials


@dataclass
class ChatMessage:
    """Stand-in for langchain_core's ChatMessage: the adapters only read these fields."""

    role: str
    content: Any
    additional_kwargs: dict = field(default_factory=dict)


ROOT = Path(__file__).resolve().parents[2] / "src/khoj"


PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def load_bodies(relative_path, names, namespace, all_functions=False):
    """Execute exact product bodies with deferred annotations and no decorators.

    `all_functions` also loads every function in the module, so a helper that product
    code starts calling (e.g. `get_usage_token_counts`) does not silently go missing
    from this harness; `names` still lists the classes and constants that must exist.
    """
    path = ROOT / relative_path
    tree = ast.parse(path.read_text(encoding="utf-8"))
    selected = []
    found = set()
    for node in tree.body:
        is_function = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        if (is_function and all_functions) or (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name in names
        ):
            node.decorator_list = []
            selected.append(node)
            found.add(node.name)
        elif isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in names for target in node.targets
        ):
            selected.append(node)
            found.update(target.id for target in node.targets if isinstance(target, ast.Name))
    assert set(names) <= found, (relative_path, set(names) - found)
    future = ast.parse("from __future__ import annotations").body
    exec(compile(ast.Module(body=future + selected, type_ignores=[]), str(path), "exec"), namespace)


@pytest.fixture
def adapter(monkeypatch):
    socket_connect = socket.socket.connect

    def deny_network(sock, address):
        # Windows asyncio creates its internal wake-up pipe via loopback TCP.
        if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1"):
            return socket_connect(sock, address)
        raise AssertionError("External network is forbidden by the SDK contract")

    monkeypatch.setattr(socket.socket, "connect", deny_network)
    for name in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_CLOUD_PROJECT"):
        monkeypatch.delenv(name, raising=False)
    captured = []
    output = {"parts": [{"text": "offline answer"}]}

    def transport(request):
        body = json.loads(request.content)
        captured.append((str(request.url), body))
        response = {
            "candidates": [{"content": {"role": "model", "parts": output["parts"]}, "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": 2, "candidatesTokenCount": 3},
        }
        if request.url.path.endswith(":predict"):
            response = {"predictions": [{"bytesBase64Encoded": output["image"], "mimeType": "image/png"}]}
        if "streamGenerateContent" in request.url.path:
            return httpx.Response(200, content=f"data: {json.dumps(response)}\n\n".encode(), headers={"content-type": "text/event-stream"})
        return httpx.Response(200, json=response)

    sync_init, async_init = httpx.Client.__init__, httpx.AsyncClient.__init__

    def init_sync(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(transport)
        sync_init(self, *args, **kwargs)

    def init_async(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(transport)
        async_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "__init__", init_sync)
    monkeypatch.setattr(httpx.AsyncClient, "__init__", init_async)
    namespace = dict(
        genai=genai, gtypes=gtypes, gerrors=genai.errors, httpx=httpx,
        json=json, logging=logging, os=os, deepcopy=deepcopy, perf_counter=perf_counter,
        io=io, Image=Image, Enum=Enum, logger=logging.getLogger(__name__), gemini_clients={},
        is_none_or_empty=lambda value: value is None or value == "",
        is_promptrace_enabled=lambda: False, get_chat_usage_metrics=lambda *a, **kw: {"offline": True},
        get_ai_api_info=lambda key, url: SimpleNamespace(api_key=key, region=None, project=None, credentials=None),
    )
    load_bodies("utils/helpers.py", {"get_gemini_client", "convert_image_to_webp", "ImageShape"}, namespace)
    load_bodies("processor/conversation/utils.py", {"ResponseWithThought", "ToolCall"}, namespace)
    load_bodies("processor/conversation/google/utils.py", {
        "GeminiRetryableClientError", "SAFETY_SETTINGS", "MAX_OUTPUT_TOKENS_FOR_REASONING_GEMINI",
        "MAX_OUTPUT_TOKENS_FOR_STANDARD_GEMINI", "MAX_REASONING_TOKENS_GEMINI",
    }, namespace, all_functions=True)
    yield namespace, captured, output
    for client in namespace["gemini_clients"].values():
        client.close()
        asyncio.run(client.aio.aclose())


def test_api_and_vertex_client_construction(adapter):
    namespace, _, _ = adapter
    api = namespace["get_gemini_client"]("synthetic-not-a-real-key")
    assert not api.vertexai
    api.close()
    namespace["get_ai_api_info"] = lambda key, url: SimpleNamespace(
        api_key=None, region="us-central1", project="synthetic-project", credentials=AnonymousCredentials()
    )
    vertex = namespace["get_gemini_client"](None)
    assert vertex.vertexai
    vertex.close()


@pytest.mark.parametrize("model,deepthought", [("gemini-2.5-flash", True), ("gemini-3-flash-preview", False)])
def test_sync_completion_uses_actual_sdk(adapter, model, deepthought):
    namespace, captured, _ = adapter
    result = namespace["gemini_completion_with_backoff"](
        [ChatMessage(role="user", content="synthetic prompt")], "synthetic system", model,
        api_key="synthetic-not-a-real-key", deepthought=deepthought, tracer={},
    )
    assert result.text == "offline answer" and result.raw_content[0]["text"] == "offline answer"
    assert len(captured) == 1
    body = captured[0][1]
    assert body["contents"][0]["parts"][0]["text"] == "synthetic prompt"
    assert body["systemInstruction"]["parts"][0]["text"] == "synthetic system"
    assert body["generationConfig"]["maxOutputTokens"] == 20000
    assert body["generationConfig"]["thinkingConfig"] == (
        {"thinking_budget": 512, "include_thoughts": True} if deepthought
        else {"thinking_level": "LOW", "include_thoughts": True}
    )


def test_async_stream_uses_actual_sdk(adapter):
    namespace, captured, output = adapter
    output["parts"] = [{"text": "synthetic thought", "thought": True}, {"text": "offline answer"}]

    async def collect():
        return [part async for part in namespace["gemini_chat_completion_with_backoff"](
            [ChatMessage(role="user", content="synthetic stream")], "gemini-2.5-flash", 0.5,
            "synthetic-not-a-real-key", None, tracer={}, deepthought=True,
        )]

    chunks = asyncio.run(collect())
    assert [part.thought for part in chunks if part.thought] == ["synthetic thought"]
    assert "".join(part.text or "" for part in chunks) == "offline answer"
    assert len(captured) == 1 and "streamGenerateContent" in captured[0][0]
    assert captured[0][1]["generationConfig"]["stopSequences"] == ["Notes:\n["]


class StaticTokenCredentials(Credentials):
    """Valid credentials with a fake bearer token: no refresh, so no token endpoint call."""

    def __init__(self):
        super().__init__()
        self.token = "synthetic-not-a-real-token"

    def refresh(self, request):
        pass


def run_image_product_path(adapter, model, config, output_png=True):
    """Call the unchanged `generate_image_with_google` body; returns (webp bytes, requests)."""
    namespace, captured, output = adapter
    namespace = dict(namespace)  # generate.py has its own format_messages_for_gemini
    load_bodies("processor/image/generate.py", set(), namespace, all_functions=True)
    png = io.BytesIO()
    Image.new("RGB", (1, 1), "white").save(png, "PNG")
    output["image"] = base64.b64encode(png.getvalue()).decode()
    output["parts"] = [{"inlineData": {"mimeType": "image/png", "data": output["image"]}}]
    image = namespace["generate_image_with_google"](
        "synthetic image", config, model, shape=namespace["ImageShape"].LANDSCAPE,
    )
    return image, captured


def assert_webp_pixel(image):
    with Image.open(io.BytesIO(image)) as decoded:
        assert decoded.format == "WEBP" and decoded.size == (1, 1)


# Names from https://ai.google.dev/gemini-api/docs/deprecations (Nano Banana models), plus
# the two the product recognised before: they must all take the generate_content path.
@pytest.mark.parametrize("model", [
    "gemini-2.5-flash-image", "gemini-3-pro-image-preview", "gemini-3-pro-image",
    "gemini-3.1-flash-image", "gemini-nano-banana-2.1",
])
def test_gemini_image_models_use_generate_content(adapter, model):
    config = SimpleNamespace(api_key="synthetic-not-a-real-key")
    image, captured = run_image_product_path(adapter, model, config)
    assert_webp_pixel(image)
    assert len(captured) == 1
    url, body = captured[0]
    assert url.endswith(f"models/{model}:generateContent")
    assert body["generationConfig"]["responseModalities"] == ["IMAGE"]
    if model.startswith("gemini-3"):
        assert body["generationConfig"]["imageConfig"]["imageSize"] == "2K"


def test_imagen_with_api_key_fails_clearly_and_sends_nothing(adapter):
    """google-genai 2.x only implements generate_images for Vertex; Google shut Imagen
    down on the Gemini Developer API (2026-08-17). Fail with advice, not an SDK error."""
    config = SimpleNamespace(api_key="synthetic-not-a-real-key")
    with pytest.raises(ValueError, match="gemini-2.5-flash-image"):
        run_image_product_path(adapter, "imagen-4.0-generate-001", config)
    assert adapter[1] == []


def test_imagen_on_vertex_still_uses_generate_images(adapter, monkeypatch):
    """Vertex users keep Imagen: the client comes from the environment, as upstream does."""
    import google.auth

    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "synthetic-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    monkeypatch.setattr(google.auth, "default", lambda *a, **kw: (StaticTokenCredentials(), "synthetic-project"))
    config = SimpleNamespace(api_key=None, ai_model_api=SimpleNamespace(api_key=None))
    image, captured = run_image_product_path(adapter, "imagen-4.0-generate-001", config)
    assert_webp_pixel(image)
    assert len(captured) == 1
    url, body = captured[0]
    assert "aiplatform.googleapis.com" in url and url.endswith("imagen-4.0-generate-001:predict")
    assert body["parameters"]["aspectRatio"] == "4:3"
    assert body["parameters"]["sampleCount"] == 1


def test_installed_sdk_is_the_version_khoj_pins():
    """The contract is only meaningful against the SDK khoj declares, not whatever is installed."""
    pinned = re.search(r'"google-genai\s*==\s*([^"\s]+)"', PYPROJECT.read_text(encoding="utf-8"))
    assert pinned, "pyproject.toml no longer pins google-genai exactly; update this contract"
    assert genai.__version__ == pinned.group(1), "run: python tools/install_contract_deps.py"
