#!/usr/bin/env python3
"""
MCP Server for Stable Diffusion (Neo Forge) - FastMCP implementation.
Provides tools for image generation, model management, and upscaling.
Uses FastMCP with Streamable HTTP transport (built-in FastAPI).
"""
from contextlib import asynccontextmanager
from io import BytesIO
import asyncio
import base64
import json
import os
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional
import logging

import httpx
import uvicorn
from PIL import Image, PngImagePlugin
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
# ------------- Configuration from environment -------------
SD_WEBUI_URL = os.environ.get("SD_WEBUI_URL", "http://127.0.0.1:7860")
AUTH_USER = os.environ.get("SD_AUTH_USER")
AUTH_PASS = os.environ.get("SD_AUTH_PASS")
DEFAULT_OUTPUT_DIR = Path(os.environ.get("SD_OUTPUT_DIR", "./output"))
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "300"))

# Upscaling defaults
SD_RESIZE_MODE = int(os.environ.get("SD_RESIZE_MODE", "0"))
SD_UPSCALE_MULTIPLIER = float(os.environ.get("SD_UPSCALE_MULTIPLIER", "4.0"))
SD_UPSCALE_WIDTH = int(os.environ.get("SD_UPSCALE_WIDTH", "512"))
SD_UPSCALE_HEIGHT = int(os.environ.get("SD_UPSCALE_HEIGHT", "512"))
SD_UPSCALER_1 = os.environ.get("SD_UPSCALER_1", "R-ESRGAN 4x+")
SD_UPSCALER_2 = os.environ.get("SD_UPSCALER_2", "None")

PORT = int(os.environ.get("PORT", "3000"))
HOST = os.environ.get("HOST", "0.0.0.0")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-sd-bridge-fastmcp")

# ------------- HTTP Client with auth -------------
_client_instance: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    """Get or create a reusable async HTTP client with optional basic auth."""
    global _client_instance
    if _client_instance is None:
        auth = None
        if AUTH_USER and AUTH_PASS:
            auth = (AUTH_USER, AUTH_PASS)

        async def log_request(request: httpx.Request) -> None:
            """Log each outgoing request (connection attempt)."""
            logger.info(
                "Connection attempt: %s %s (base_url=%s)",
                request.method,
                request.url,
                SD_WEBUI_URL,
            )

        async def log_response(response: httpx.Response) -> None:
            """Log each response received."""
            logger.info(
                "Connection result: %s %s -> %s %s",
                response.request.method,
                response.request.url,
                response.status_code,
                response.reason_phrase,
            )

        _client_instance = httpx.AsyncClient(
            base_url=SD_WEBUI_URL,
            timeout=REQUEST_TIMEOUT,
            auth=auth,
            headers={"Content-Type": "application/json"},
            event_hooks={
                "request": [log_request],
                "response": [log_response],
            },
        )
        logger.info(
            "HTTP client initialized: base_url=%s, auth=%s, timeout=%s",
            SD_WEBUI_URL,
            "enabled" if auth else "disabled",
            REQUEST_TIMEOUT,
        )
    return _client_instance


async def close_http_client() -> None:
    """Close the HTTP client on shutdown."""
    global _client_instance
    if _client_instance is not None:
        await _client_instance.aclose()
        _client_instance = None


# ------------- Helper functions -------------
async def ensure_directory(path: Path) -> None:
    """Create directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)


def encode_image(image_path: Path) -> str:
    """Read image file and return base64 encoded string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def decode_base64_to_image(base64_str: str) -> bytes:
    """Decode base64 string to image bytes."""
    if "," in base64_str:
        base64_str = base64_str.split(",", 1)[1]
    return base64.b64decode(base64_str)


async def save_image_with_metadata(
    image_data: bytes,
    png_info: str,
    output_dir: Path,
) -> Path:
    """Save image as PNG with embedded parameters in metadata."""
    await ensure_directory(output_dir)
    filename = f"sd_{uuid.uuid4()}.png"
    filepath = output_dir / filename

    # Open image using PIL
    img = Image.open(BytesIO(image_data))
    # Add metadata
    meta = PngImagePlugin.PngInfo()
    if png_info:
        meta.add_text("Description", png_info)
    img.save(filepath, "PNG", pnginfo=meta)
    return filepath


# ------------- Pydantic models for tool arguments -------------
class GenerateImageArgs(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = None
    steps: int = Field(default=4, ge=1, le=150)
    width: int = Field(default=1024, ge=512, le=2048)
    height: int = Field(default=1024, ge=512, le=2048)
    cfg_scale: float = Field(default=1.0, ge=1.0, le=30.0)
    sampler_name: str = Field(default="Euler")
    scheduler_name: str = Field(default="Simple")
    seed: int = Field(default=-1, ge=-1)
    batch_size: int = Field(default=1, ge=1, le=4)
    restore_faces: bool = False
    tiling: bool = False
    distilled_cfg_scale: Optional[float] = Field(default=3.5, ge=1.0, le=30.0)
    output_path: Optional[str] = None


class SetModelArgs(BaseModel):
    model_name: str


class UpscaleImagesArgs(BaseModel):
    images: List[str]
    resize_mode: Optional[int] = Field(default=None, ge=0, le=1)
    upscaling_resize: Optional[float] = Field(default=None, gt=0)
    upscaling_resize_w: Optional[int] = Field(default=None, gt=0)
    upscaling_resize_h: Optional[int] = Field(default=None, gt=0)
    upscaler_1: Optional[str] = None
    upscaler_2: Optional[str] = None
    output_path: Optional[str] = None


# ------------- FastMCP Server -------------
mcp = FastMCP(
    "NeoForgeBridge",
    stateless_http=True,
)


# ------------- Tool handlers as FastMCP tools -------------
@mcp.tool()
async def generate_image(args: GenerateImageArgs) -> str:
    """Generate an image using Stable Diffusion (txt2img).

    Args:
        args: Generation parameters including prompt, dimensions, sampler, etc.
    """
    client = get_http_client()
    output_dir = Path(args.output_path) if args.output_path else DEFAULT_OUTPUT_DIR
    await ensure_directory(output_dir)

    payload = {
        "prompt": args.prompt,
        "negative_prompt": args.negative_prompt or "",
        "steps": args.steps,
        "width": args.width,
        "height": args.height,
        "cfg_scale": args.cfg_scale,
        "sampler_name": args.sampler_name,
        "scheduler": args.scheduler_name,
        "seed": args.seed,
        "n_iter": args.batch_size,
        "restore_faces": args.restore_faces,
        "tiling": args.tiling,
        "distilled_cfg_scale": args.distilled_cfg_scale or 3.5,
    }

    resp = await client.post("/sdapi/v1/txt2img", json=payload)
    resp.raise_for_status()
    data = resp.json()

    if not data.get("images"):
        raise RuntimeError("No images generated")

    results = []
    for img_b64 in data["images"]:
        # Get PNG info
        png_info_resp = await client.post(
            "/sdapi/v1/png-info",
            json={"image": f"data:image/png;base64,{img_b64}"}
        )
        png_info_resp.raise_for_status()
        png_info = png_info_resp.json().get("info", "")

        # Decode and save
        image_bytes = decode_base64_to_image(img_b64)
        filepath = await save_image_with_metadata(image_bytes, png_info, output_dir)
        results.append({
            "path": str(filepath),
            "parameters": png_info,
        })

    return json.dumps(results)


@mcp.tool()
async def get_sd_models() -> str:
    """Get list of available Stable Diffusion models."""
    client = get_http_client()
    resp = await client.get("/sdapi/v1/sd-models")
    resp.raise_for_status()
    models = resp.json()
    titles = [m.get("title") for m in models if m.get("title")]
    return json.dumps(titles)


@mcp.tool()
async def set_sd_model(args: SetModelArgs) -> str:
    """Set the active Stable Diffusion model.

    Args:
        args: Model name to set as active.
    """
    client = get_http_client()
    resp = await client.post(
        "/sdapi/v1/options",
        json={"sd_model_checkpoint": args.model_name}
    )
    resp.raise_for_status()
    return f"Model set to: {args.model_name}"


@mcp.tool()
async def get_sd_upscalers() -> str:
    """Get list of available upscaler models."""
    client = get_http_client()
    resp = await client.get("/sdapi/v1/upscalers")
    resp.raise_for_status()
    upscalers = resp.json()
    names = [u.get("name") for u in upscalers if u.get("name")]
    return json.dumps(names)


@mcp.tool()
async def upscale_images(args: UpscaleImagesArgs) -> str:
    """Upscale one or more images using Stable Diffusion.

    Args:
        args: Images to upscale with upscaling parameters.
    """
    client = get_http_client()
    output_dir = Path(args.output_path) if args.output_path else DEFAULT_OUTPUT_DIR
    await ensure_directory(output_dir)

    # Read and encode images
    image_list = []
    for img_path_str in args.images:
        img_path = Path(img_path_str)
        if not img_path.exists():
            raise FileNotFoundError(f"Image not found: {img_path_str}")
        encoded = encode_image(img_path)
        image_list.append({
            "data": encoded,
            "name": img_path.name,
        })

    # Build payload
    resize_mode = args.resize_mode if args.resize_mode is not None else SD_RESIZE_MODE
    upscaling_resize = args.upscaling_resize if args.upscaling_resize is not None else SD_UPSCALE_MULTIPLIER
    upscaling_resize_w = args.upscaling_resize_w if args.upscaling_resize_w is not None else SD_UPSCALE_WIDTH
    upscaling_resize_h = args.upscaling_resize_h if args.upscaling_resize_h is not None else SD_UPSCALE_HEIGHT
    upscaler_1 = args.upscaler_1 if args.upscaler_1 is not None else SD_UPSCALER_1
    upscaler_2 = args.upscaler_2 if args.upscaler_2 is not None else SD_UPSCALER_2

    payload = {
        "resize_mode": resize_mode,
        "show_extras_results": True,
        "gfpgan_visibility": 0,
        "codeformer_visibility": 0,
        "codeformer_weight": 0,
        "upscaling_resize": upscaling_resize,
        "upscaling_resize_w": upscaling_resize_w,
        "upscaling_resize_h": upscaling_resize_h,
        "upscaling_crop": False,
        "upscaler_1": upscaler_1,
        "upscaler_2": upscaler_2,
        "extras_upscaler_2_visibility": 0,
        "upscale_first": False,
        "imageList": image_list,
    }

    resp = await client.post("/sdapi/v1/extra-batch-images", json=payload)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for img_data in data.get("images", []):
        # Each image has "data" (base64) and possibly "info"
        img_b64 = img_data.get("data")
        if not img_b64:
            continue
        image_bytes = decode_base64_to_image(img_b64)
        # Save without metadata (or use png-info if needed)
        filepath = output_dir / f"upscaled_{uuid.uuid4()}.png"
        img = Image.open(BytesIO(image_bytes))
        img.save(filepath, "PNG")
        results.append(str(filepath))

    return json.dumps(results)


# ------------- Starlette lifespan for clean shutdown -------------
@asynccontextmanager
async def lifespan(app: Any) -> AsyncGenerator[None, None]:
    """Handle application lifespan: cleanup HTTP client on shutdown."""
    try:
        yield
    finally:
        await close_http_client()


# ------------- Starlette application from FastMCP -------------
class HostFixMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Подменяем Host на локальный, чтобы проверка прошла
        request.scope["headers"] = [
            (b"host", b"localhost:3000") if k == b"host" else (k, v)
            for k, v in request.scope["headers"]
        ]
        return await call_next(request)

app = mcp.streamable_http_app()
app.add_middleware(HostFixMiddleware)
app.lifespan = lifespan


# ------------- Main entry point -------------
async def main():
    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="info")
    server_uvicorn = uvicorn.Server(config)
    logger.info(f"Starting FastMCP SD bridge on {HOST}:{PORT}")
    await server_uvicorn.serve()


if __name__ == "__main__":
    asyncio.run(main())