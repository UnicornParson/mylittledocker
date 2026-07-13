# SPDX-FileCopyrightText: 2026 https://github.com/kurtzhi/fsext-mcp-server-python
# SPDX-License-Identifier: Apache-2.0

# Copyright 2026 https://github.com/kurtzhi/fsext-mcp-server-python
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Image processing & OCR MCP tool module
Provides image resizing, cropping, rotation and Tesseract text extraction tools.
All file path parameters are restricted within the allowed workspace directory.
"""
from typing import Optional

from .._instance import mcp
from ..path_restrict import restrict_workspace
from ..response_helper import response_helper
from ..util import (image, ocr)


@mcp.tool()
@response_helper
@restrict_workspace(path_argument_names=["source_path", "dest_path"])
async def fs_image_resize(
        source_path: str,
        dest_path: str,
        width: int,
        height: int,
        keep_aspect_ratio: Optional[bool] = True,
        pad_to_target: Optional[bool] = True
) -> dict:
    """Resize image with ratio lock and padding support."""
    image.resize(source_path, dest_path, width,
                 height, keep_aspect_ratio, pad_to_target)
    return {}


@mcp.tool()
@response_helper
@restrict_workspace(path_argument_names=["source_path", "dest_path"])
async def fs_image_crop(
        source_path: str,
        dest_path: str,
        x: int,
        y: int,
        width: int,
        height: int
) -> dict:
    """Crop rectangular region from image."""
    image.crop(source_path, dest_path, x, y, width, height)
    return {}


@mcp.tool()
@response_helper
@restrict_workspace(path_argument_names=["source_path", "dest_path"])
async def fs_image_rotate(
        source_path: str,
        dest_path: str,
        degrees: float
) -> dict:
    """Rotate image clockwise, expand canvas to retain full content."""
    image.rotate_image(source_path, dest_path, degrees)
    return {}


@mcp.tool()
@response_helper
@restrict_workspace(path_argument_names=["image_path"])
async def fs_ocr_extract_text(
        image_path: str,
        tesseract_bin_path: Optional[str] = "",
        tessdata_path: Optional[str] = "",
        lang: Optional[str] = "eng"
) -> dict:
    """Extract text from image via Tesseract OCR."""
    content = ocr.extract_text(image_path, tesseract_bin_path, tessdata_path, lang)
    return {"content": content}
