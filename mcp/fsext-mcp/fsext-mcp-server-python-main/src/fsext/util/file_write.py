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
Service for writing text and binary content to files with safety permission validation.
"""
from pathlib import Path

from .check_utils import (
    require_non_blank,
    require_writable_file,
    require_writable_parent_directory
)


def write_text_file(file_path: str, text: str, append: bool = False, charset: str = "utf-8"):
    """
    Write UTF-8 text content to target file, support overwrite or append mode.

    :param file_path: The path to the target file.
    :param text: The string content to write.
    :param append: If true, appends the text; otherwise, overwrites existing file content.
    :param charset: Text decode character encoding
    :raises ValueError: file_path is blank string
    :raises ValueError: Target file or parent directory lacks write permission
    """
    require_non_blank(file_path, "file_path")

    path = Path(file_path)
    if path.exists():
        require_writable_file(path, "file_path")
    else:
        require_writable_parent_directory(path, "file_path")

    mode = "a" if append else "w"
    with open(path, mode, encoding=charset) as writer:
        writer.write(text)


def write_binary_file(
        file_path: str,
        data: bytes,
        offset: int = 0,
        length: int = -1,
        append: bool = False,
):
    """
    Write sliced binary bytes to target file, support overwrite or append mode.
    Slice source byte data by specified offset and length before writing.

    :param file_path: The path to the target file.
    :param data: Source raw byte buffer to extract write content from, cannot be empty bytes.
    :param offset: Start slice position of source byte buffer.
    :param length: Max byte count to write; -1 means read all remaining bytes from offset.
    :param append: If true, appends bytes to file tail; otherwise truncates and overwrites file.
    :raises ValueError: file_path is blank string, data is empty bytes, offset/length out of data buffer bounds
    :raises ValueError: Target file or parent directory lacks write permission
    :raises OSError: Disk full, file locked or deleted during write operation
    """
    require_non_blank(file_path, "file_path")

    if not data or len(data) == 0:
        raise ValueError("Invalid data or invalid length of the data")

    if length == -1:
        length = len(data) - offset
    # Validate source buffer slice boundary
    if offset < 0 or length < 0 or offset + length > len(data):
        raise ValueError("Invalid offset or length for byte array")

    path = Path(file_path)

    if path.exists():
        require_writable_file(path, "file_path")
    else:
        require_writable_parent_directory(path, "file_path")

    mode = "ab" if append else "wb"
    with open(path, mode) as f:
        # Slice source bytes by given offset and length then flush to file
        f.write(data[offset: offset + length])
