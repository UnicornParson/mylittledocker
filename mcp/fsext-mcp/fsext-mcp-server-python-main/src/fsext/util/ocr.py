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
Service for performing Optical Character Recognition (OCR) on images via Tesseract.
All file and directory path inputs are validated through unified check_utils utilities.
"""
import os
import re
from pathlib import Path

import pytesseract
from PIL import Image

from .check_utils import (
    require_non_blank,
    require_readable_file,
    require_readable_directory
)


def extract_text(
        image_path: str,
        tesseract_bin_path: str = "",
        tessdata_path: str = "",
        lang: str = "eng",
) -> str:
    """
    Extract text content from image file using Tesseract OCR engine.

    :param image_path: The path to the source image file.
    :param tesseract_bin_path: Full path of Tesseract executable binary.
    :param tessdata_path: Optional directory path for Tesseract language data files.
    :param lang: OCR language code (e.g. "eng", "chi_sim").
    :return: Raw plain text extracted from image.
    :raises ValueError: Mandatory argument blank; target path not readable file/directory
    """
    require_non_blank(image_path, "image_path")
    input_file = Path(image_path)
    require_readable_file(input_file, "image")

    require_non_blank(tesseract_bin_path, "tesseract_bin_path")
    tesseract_bin_file = Path(tesseract_bin_path)
    require_readable_file(tesseract_bin_file, "tesseract_bin_path")

    require_non_blank(lang, "lang")

    custom_config = f'--dpi 96'
    if tessdata_path:
        require_non_blank(tessdata_path, "tessdata_path")
        tessdata_dir = Path(tessdata_path)
        require_readable_directory(tessdata_dir, "tessdata_path")
        custom_config += f' --tessdata-dir {str(tessdata_dir)}'
        os.environ["TESSDATA_PREFIX"] = str(tessdata_dir)

    # Override tesseract binary path for pytesseract runtime
    pytesseract.pytesseract.tesseract_cmd = str(tesseract_bin_file)  # type: ignore

    with Image.open(input_file) as img:
        text = pytesseract.image_to_string(img, lang=lang, config=custom_config)

    return text


def clean_ocr_text(raw: str) -> str:
    """
    Optional OCR text cleaner for keyword search scenarios.
    Preserve raw text if you need complete audit/evidence data.
    Remove url fragments, messy single noise symbols, extra whitespace.
    :param raw: Original full text output from OCR service
    :return: Clean compact text optimized for keyword matching
    """
    if not raw:
        return ""
    # Remove all http/https links
    text = re.sub(r"https?:\/\/[\w\.\/:@#\-]+", "", raw)
    # Remove scattered noise symbols
    text = re.sub(r"[@#\[\]Wm«»()]", "", text)
    # Collapse multiple whitespace, newlines, tabs to single space
    text = re.sub(r"\s+", " ", text)
    return text.strip()
