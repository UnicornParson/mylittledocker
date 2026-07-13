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
Service for performing image-related operations, including mime detection, resize, crop and rotation.
All file path arguments are validated via unified check_utils utilities.
"""
from pathlib import Path

from PIL import Image
from PIL.Image import Resampling

from .file import get_file_extension
from .check_utils import (
    require_non_blank,
    require_readable_file,
    require_writable_parent_directory
)


def resize(
        source_path: str,
        dest_path: str,
        width: int,
        height: int,
        keep_aspect_ratio: bool,
        pad_to_target: bool,
):
    """
    Resizes an image from the source path to the specified target dimensions, supports transparent padding.
    Auto switch canvas color mode to avoid save failure for non-alpha formats like JPG.

    :param source_path: The path to the source image.
    :param dest_path: The path to save the resized image.
    :param width: Target canvas pixel width, must be positive integer.
    :param height: Target canvas pixel height, must be positive integer.
    :param keep_aspect_ratio: If true, maintains the original aspect ratio with thumbnail scaling.
    :param pad_to_target: If true, fill blank space with padding to target canvas size.
    :raises ValueError: Path arguments blank, source unreadable file, destination parent not writable,
                        target_width/target_height <= 0
    """
    require_non_blank(source_path, "source_path")
    require_non_blank(dest_path, "dest_path")

    if width <= 0 or height <= 0:
        raise ValueError("target_width and target_height must be positive integers")

    src_img = Path(source_path)
    require_readable_file(src_img, "source_path")

    dst_img = Path(dest_path)
    require_writable_parent_directory(dst_img, "dest_path")
    output_format = get_file_extension(dest_path, "dest_path").lower()

    with Image.open(src_img) as img:
        if keep_aspect_ratio:
            img.thumbnail((width, height))
            actual_width, actual_height = img.size
        else:
            img = img.resize((width, height), resample=Resampling.LANCZOS)
            actual_width, actual_height = width, height

        if pad_to_target:
            if output_format in ("jpg", "jpeg"):
                fill_color = (255, 255, 255)
                canvas_mode = "RGB"
            else:
                fill_color = (255, 255, 255, 0)
                canvas_mode = "RGBA"
            new_img = Image.new(canvas_mode, (width, height), fill_color)
            new_img.paste(
                img, ((width - actual_width) // 2, (height - actual_height) // 2)
            )
            new_img.save(dst_img)
        else:
            img.save(dst_img)


def crop(
        source_path: str,
        dest_path: str,
        x: int,
        y: int,
        width: int,
        height: int,
):
    """
    Crops a rectangular sub-region from an image and saves to destination path.
    Pillow crop format: (left, upper, right, lower). All size params must be >= 0.

    :param source_path: The path to the source image.
    :param dest_path: The path to save the cropped image.
    :param x: X coordinate of crop region top-left corner (pixel), >=0
    :param y: Y coordinate of crop region top-left corner (pixel), >=0
    :param width: Pixel width of crop box, must be positive
    :param height: Pixel height of crop box, must be positive
    :raises ValueError: Path arguments blank, source unreadable file, destination parent not writable,
                        negative crop coordinate/size
    """
    require_non_blank(source_path, "source_path")
    src_img = Path(source_path)
    require_readable_file(src_img, "image_path")

    if x < 0 or y < 0 or width <= 0 or height <= 0:
        raise ValueError("Crop x/y cannot be negative, width/height must be positive")

    require_non_blank(dest_path, "dest_path")
    dst_img = Path(dest_path)
    require_writable_parent_directory(dst_img, "dest_path")

    with Image.open(src_img) as img:
        # Pillow crop format: (left, upper, right, lower)
        cropped_img = img.crop((x, y, x + width, y + height))
        cropped_img.save(dst_img)


def rotate_image(
        source_path: str,
        dest_path: str,
        degrees: float
):
    """
    Rotates an image by specified clockwise degrees, expand canvas to avoid content cropping.
    Pillow native rotate is counter-clockwise, negative degree converts to clockwise rotation.

    :param source_path: The path to the source image.
    :param dest_path: The path to save the rotated image.
    :param degrees: Clockwise rotation angle in floating-point degrees.
    :raises ValueError: Path arguments blank, source unreadable file, destination parent not writable
    """
    require_non_blank(source_path, "source_path")
    src_img = Path(source_path)
    require_readable_file(src_img, "image_path")

    require_non_blank(dest_path, "dest_path")
    dst_img = Path(dest_path)
    require_writable_parent_directory(dst_img, "dest_path")

    degrees = degrees % 360

    with Image.open(src_img) as source:
        # expand=True auto enlarge canvas to hold full rotated content, BICUBIC for smooth resample
        rotated_image = source.rotate(-degrees, expand=True, resample=Resampling.BICUBIC)
        rotated_image.save(fp=dst_img)
