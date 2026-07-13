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
Utility methods for file reading, supports text line range and binary partial read.
All file path arguments are validated via unified check_utils utilities.
"""
from io import UnsupportedOperation
from pathlib import Path
from typing import NamedTuple, Optional

from .check_utils import (
    require_non_blank,
    require_readable_file,
    MAX_INT
)


class ReadResultString(NamedTuple):
    """
    Text file read result container.
    """
    lines_count: int
    content: str


class ReadResultBytes(NamedTuple):
    """
    Binary file partial read result container.
    """
    bytes: bytearray
    actual_length: int
    end_of_stream: bool


def read_text_file(file_path: str, charset: str = "utf-8") -> ReadResultString:
    """
    Reads entire text file, wraps read_text_file_range with no skip and unlimited read lines.

    :param file_path: String path of target text file
    :param charset: Text decode character encoding
    :return: ReadResultString with total line count and full file content
    """
    return read_text_file_range(file_path, 0, MAX_INT, "\n", charset)


def read_text_file_range(
        file_path: str,
        lines_to_skip: int,
        max_lines_to_read: int,
        line_separator: str = "\n",
        charset: str = "utf-8",
) -> ReadResultString:
    """
    Read sliced line range from text file, support skip leading lines and read line limit.

    :param file_path: String path of target text file
    :param lines_to_skip: Count of leading lines to skip; negative value treated as 0
    :param max_lines_to_read: Max lines to collect; negative value means read all remaining lines
    :param line_separator: Separator string used to concatenate collected lines
    :param charset: Text file decode encoding
    :return: ReadResultString with collected line count and joined text content
    :raises ValueError: If file_path is empty or whitespace-only
    :raises ValueError: If target path is not a readable regular file
    :raises UnicodeDecodeError: File cannot be decoded with specified charset
    """
    require_non_blank(file_path, "file_path")
    p = Path(file_path)
    require_readable_file(p, "file_path")

    skip = max(lines_to_skip, 0)
    max_lines = max_lines_to_read if max_lines_to_read > 0 else MAX_INT

    lines = []
    lines_count = 0

    with open(p, "r", encoding=charset) as f:

        for i, line in enumerate(f):
            if i >= skip:
                if len(lines) < max_lines:
                    lines.append(line.rstrip("\r\n"))
                    lines_count += 1
                else:
                    break

    return ReadResultString(lines_count, line_separator.join(lines))


def read_binary_file(
        file_path: str,
        buffer: Optional[bytearray] = None,
        bytes_to_skip: int = -1,
        max_bytes_to_read: int = -1,
) -> ReadResultBytes:
    """
    Partial binary file read with offset skip and length limit, support external output buffer reuse.
    Note: Uses seek for random access, does not support pipe/stdin/socket non-seekable streams.

    :param file_path: String path of target binary file
    :param buffer: Reusable bytearray for storing read bytes; auto create new empty buffer if None
    :param bytes_to_skip: Byte offset to skip from file head; negative value treated as 0
    :param max_bytes_to_read: Max byte length to read; negative value means read all remaining bytes
    :return: ReadResultBytes contains filled buffer, actual read byte count and EOF flag
    :raises ValueError: If file_path is empty or whitespace-only
    :raises ValueError: If target path is not a readable regular file
    :raises io.UnsupportedOperation: Target stream does not support seek random access
    """
    require_non_blank(file_path, "file_path")
    p = Path(file_path)
    require_readable_file(p, "file_path")

    given_buffer_len = len(buffer) if buffer is not None else 0
    if buffer and (given_buffer_len == 0 or given_buffer_len < max_bytes_to_read):
        raise ValueError(f"max_bytes_to_read must be > 0, and buffer length must be >= maxBytesToRead. got "
                         f"max_bytes_to_read = '{max_bytes_to_read}', buffer.length = '{given_buffer_len}'")

    file_size = p.stat().st_size
    skip = max(bytes_to_skip, 0)
    max_bytes_to_read = max_bytes_to_read if max_bytes_to_read > 0 else given_buffer_len

    if skip >= file_size:
        return ReadResultBytes(bytearray(), 0, True)

    with open(p, "rb") as f:
        try:
            f.seek(skip)
        except UnsupportedOperation as e:
            raise IOError(f"File '{file_path}' does not support random seek access") from e

        bytes_to_read = max_bytes_to_read if max_bytes_to_read > 0 else file_size - skip
        data = f.read(bytes_to_read)

    actual_length = len(data)
    end_of_stream = (skip + actual_length) >= file_size

    if buffer is None:
        buffer = bytearray(actual_length)
    elif len(buffer) < actual_length:
        buffer = bytearray(actual_length)

    buffer[:actual_length] = data

    return ReadResultBytes(buffer, actual_length, end_of_stream)
