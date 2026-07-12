#!/usr/bin/env python3
"""
MCP Server for Stable Diffusion (Neo Forge) - Python implementation.
Provides tools for image generation, model management, and upscaling.
Uses the official MCP Python SDK with SSE transport.
"""
from io import BytesIO
import asyncio
import base64
import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

import httpx
import uvicorn
from PIL import Image, PngImagePlugin
from pydantic import BaseModel, Field
from starlette.applications import Starlette
from starlette.routing import Mount

from mcp.server import Server
from mcp.server.sse import SseServerTransport
import mcp.types as types
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
logger = logging.getLogger("mcp-sd-bridge")

# ------------- HTTP Client with auth -------------
def create_http_client() -> httpx.AsyncClient:
    """Create an async HTTP client with optional basic auth."""
    auth = None
    if AUTH_USER and AUTH_PASS:
        auth = (AUTH_USER, AUTH_PASS)
    return httpx.AsyncClient(
        base_url=SD_WEBUI_URL,
        timeout=REQUEST_TIMEOUT,
        auth=auth,
        headers={"Content-Type": "application/json"},
    )

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

# ------------- Tool argument models (for validation) -------------
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

# ------------- MCP Server -------------
server = Server("image-gen")

@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List all available tools."""
    return [
        types.Tool(
            name="generate_image",
            description="Generate an image using Stable Diffusion",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The prompt describing the desired image"},
                    "negative_prompt": {"type": "string", "description": "Things to exclude from the image"},
                    "steps": {"type": "number", "description": "Number of sampling steps (default: 4)", "minimum": 1, "maximum": 150},
                    "width": {"type": "number", "description": "Image width (default: 1024)", "minimum": 512, "maximum": 2048},
                    "height": {"type": "number", "description": "Image height (default: 1024)", "minimum": 512, "maximum": 2048},
                    "cfg_scale": {"type": "number", "description": "CFG scale (default: 1)", "minimum": 1, "maximum": 30},
                    "sampler_name": {"type": "string", "description": "Sampling algorithm (default: Euler)", "default": "Euler"},
                    "scheduler_name": {"type": "string", "description": "Scheduler algorithm (default: Simple)", "default": "Simple"},
                    "seed": {"type": "number", "description": "Random seed (-1 for random)", "minimum": -1},
                    "batch_size": {"type": "number", "description": "Number of images to generate (default: 1)", "minimum": 1, "maximum": 4},
                    "restore_faces": {"type": "boolean", "description": "Enable face restoration"},
                    "tiling": {"type": "boolean", "description": "Generate tileable images"},
                    "distilled_cfg_scale": {"type": "number", "description": "Distilled CFG scale (default: 3.5)", "minimum": 1, "maximum": 30},
                    "output_path": {"type": "string", "description": "Custom output path for the generated image"},
                },
                "required": ["prompt"],
            },
        ),
        types.Tool(
            name="get_sd_models",
            description="Get list of available Stable Diffusion models",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="set_sd_model",
            description="Set the active Stable Diffusion model",
            inputSchema={
                "type": "object",
                "properties": {
                    "model_name": {"type": "string", "description": "Name of the model to set as active"},
                },
                "required": ["model_name"],
            },
        ),
        types.Tool(
            name="get_sd_upscalers",
            description="Get list of available upscaler models",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="upscale_images",
            description="Upscale one or more images using Stable Diffusion",
            inputSchema={
                "type": "object",
                "properties": {
                    "images": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of image file paths to upscale",
                    },
                    "resize_mode": {
                        "type": "number",
                        "enum": [0, 1],
                        "description": "0 for multiplier mode (default), 1 for dimension mode",
                    },
                    "upscaling_resize": {
                        "type": "number",
                        "description": "Upscale multiplier (default: 4) - used when resize_mode is 0",
                    },
                    "upscaling_resize_w": {
                        "type": "number",
                        "description": "Target width in pixels (default: 512) - used when resize_mode is 1",
                    },
                    "upscaling_resize_h": {
                        "type": "number",
                        "description": "Target height in pixels (default: 512) - used when resize_mode is 1",
                    },
                    "upscaler_1": {
                        "type": "string",
                        "description": "Primary upscaler model (default: R-ESRGAN 4x+)",
                    },
                    "upscaler_2": {
                        "type": "string",
                        "description": "Secondary upscaler model (default: None)",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Custom output directory for upscaled images",
                    },
                },
                "required": ["images"],
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: Dict[str, Any]
) -> List[types.TextContent]:
    """Handle tool execution."""
    try:
        async with create_http_client() as client:
            if name == "generate_image":
                return await handle_generate_image(client, arguments)
            elif name == "get_sd_models":
                return await handle_get_models(client)
            elif name == "set_sd_model":
                return await handle_set_model(client, arguments)
            elif name == "get_sd_upscalers":
                return await handle_get_upscalers(client)
            elif name == "upscale_images":
                return await handle_upscale_images(client, arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        logger.exception("Error in tool execution")
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]

# ------------- Tool handlers -------------
async def handle_generate_image(client: httpx.AsyncClient, args: Dict[str, Any]) -> List[types.TextContent]:
    """Generate image using txt2img API."""
    parsed = GenerateImageArgs(**args)
    output_dir = Path(parsed.output_path) if parsed.output_path else DEFAULT_OUTPUT_DIR
    await ensure_directory(output_dir)

    payload = {
        "prompt": parsed.prompt,
        "negative_prompt": parsed.negative_prompt or "",
        "steps": parsed.steps,
        "width": parsed.width,
        "height": parsed.height,
        "cfg_scale": parsed.cfg_scale,
        "sampler_name": parsed.sampler_name,
        "scheduler": parsed.scheduler_name,
        "seed": parsed.seed,
        "n_iter": parsed.batch_size,
        "restore_faces": parsed.restore_faces,
        "tiling": parsed.tiling,
        "distilled_cfg_scale": parsed.distilled_cfg_scale or 3.5,
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

    return [types.TextContent(type="text", text=json.dumps(results))]

async def handle_get_models(client: httpx.AsyncClient) -> List[types.TextContent]:
    """Get list of available models."""
    resp = await client.get("/sdapi/v1/sd-models")
    resp.raise_for_status()
    models = resp.json()
    titles = [m.get("title") for m in models if m.get("title")]
    return [types.TextContent(type="text", text=json.dumps(titles))]

async def handle_set_model(client: httpx.AsyncClient, args: Dict[str, Any]) -> List[types.TextContent]:
    """Set active model."""
    parsed = SetModelArgs(**args)
    resp = await client.post(
        "/sdapi/v1/options",
        json={"sd_model_checkpoint": parsed.model_name}
    )
    resp.raise_for_status()
    return [types.TextContent(type="text", text=f"Model set to: {parsed.model_name}")]

async def handle_get_upscalers(client: httpx.AsyncClient) -> List[types.TextContent]:
    """Get list of available upscalers."""
    resp = await client.get("/sdapi/v1/upscalers")
    resp.raise_for_status()
    upscalers = resp.json()
    names = [u.get("name") for u in upscalers if u.get("name")]
    return [types.TextContent(type="text", text=json.dumps(names))]

async def handle_upscale_images(client: httpx.AsyncClient, args: Dict[str, Any]) -> List[types.TextContent]:
    """Upscale one or more images using extra-batch-images API."""
    parsed = UpscaleImagesArgs(**args)
    output_dir = Path(parsed.output_path) if parsed.output_path else DEFAULT_OUTPUT_DIR
    await ensure_directory(output_dir)

    # Read and encode images
    image_list = []
    for img_path_str in parsed.images:
        img_path = Path(img_path_str)
        if not img_path.exists():
            raise FileNotFoundError(f"Image not found: {img_path_str}")
        encoded = encode_image(img_path)
        image_list.append({
            "data": encoded,
            "name": img_path.name,
        })

    # Build payload
    resize_mode = parsed.resize_mode if parsed.resize_mode is not None else SD_RESIZE_MODE
    upscaling_resize = parsed.upscaling_resize if parsed.upscaling_resize is not None else SD_UPSCALE_MULTIPLIER
    upscaling_resize_w = parsed.upscaling_resize_w if parsed.upscaling_resize_w is not None else SD_UPSCALE_WIDTH
    upscaling_resize_h = parsed.upscaling_resize_h if parsed.upscaling_resize_h is not None else SD_UPSCALE_HEIGHT
    upscaler_1 = parsed.upscaler_1 if parsed.upscaler_1 is not None else SD_UPSCALER_1
    upscaler_2 = parsed.upscaler_2 if parsed.upscaler_2 is not None else SD_UPSCALER_2

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

    return [types.TextContent(type="text", text=json.dumps(results))]

# ------------- SSE Transport & ASGI application -------------
sse_transport = SseServerTransport("/mcp/")


async def _handle_post_message(scope, receive, send):
    """Wrapper to handle POST messages (delegates to SseServerTransport)."""
    await sse_transport.handle_post_message(scope, receive, send)


async def sse_app(scope, receive, send):
    """ASGI application: GET → establish SSE stream, POST → message handling."""
    if scope["method"] == "GET":
        async with sse_transport.connect_sse(scope, receive, send) as streams:
            read_stream, write_stream = streams
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )
    else:
        await _handle_post_message(scope, receive, send)


mcp_app = Starlette(
    routes=[
        Mount("/mcp", app=sse_app),
    ]
)

async def main():
    config = uvicorn.Config(mcp_app, host=HOST, port=PORT, log_level="info")
    server_uvicorn = uvicorn.Server(config)
    logger.info(f"Starting MCP SD bridge on {HOST}:{PORT}")
    await server_uvicorn.serve()

if __name__ == "__main__":
    asyncio.run(main())
