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
File read & write MCP tool module
Supports full/slice text reading, chunked binary reading, text/binary file writing.
All file access paths are limited to the permitted workspace scope.
"""
import base64
from typing import Optional

from .._instance import mcp
from ..path_restrict import restrict_workspace
from ..response_helper import response_helper
from ..util import (file_read, file_write)
from ..util.check_utils import require_non_blank
from .charset import Charset


@mcp.tool()
@response_helper
@restrict_workspace(path_argument_names=["file_path"])
async def fs_read_full_text(
        file_path: str,
        charset: Optional[Charset] = Charset.UTF8
) -> dict:
    """Read full text file."""
    res = file_read.read_text_file(file_path, charset)
    return {"content": res.content}


@mcp.tool()
@response_helper
@restrict_workspace(path_argument_names=["file_path"])
async def fs_read_text_range(
        file_path: str,
        lines_to_skip: int,
        max_lines_to_read: int,
        line_separator: Optional[str] = "\n",
        charset: Optional[Charset] = Charset.UTF8
) -> dict:
    """Read sliced text segment, -1 unlimited."""
    res = file_read.read_text_file_range(file_path, lines_to_skip, max_lines_to_read, line_separator, charset)
    return {
        "lines_count": res.lines_count,
        "content": res.content
    }


@mcp.tool()
@response_helper
@restrict_workspace(path_argument_names=["file_path"])
async def fs_read_binary_chunk(
        file_path: str,
        bytes_to_skip: int = 0,
        max_bytes_to_read: int = 0
) -> dict:
    """Partial binary read, base64 output, 0 unlimited."""
    res = file_read.read_binary_file(file_path, None, bytes_to_skip, max_bytes_to_read)
    b64 = base64.b64encode(res.bytes).decode("iso-8859-1")
    return {
        "data_base64": b64,
        "raw_bytes_length": res.actual_length,
        "end_of_stream": res.end_of_stream
    }


@mcp.tool()
@response_helper
@restrict_workspace(path_argument_names=["file_path"])
async def fs_write_text(
        file_path: str,
        text: str,
        append: bool = False,
        charset: Optional[Charset] = Charset.UTF8
) -> dict:
    """Write text file, append or overwrite."""
    file_write.write_text_file(file_path, text, append, charset)
    return {}


@mcp.tool()
@response_helper
@restrict_workspace(path_argument_names=["file_path"])
async def fs_write_binary(
        file_path: str,
        base64_data: str,
        append: bool = False
) -> dict:
    """Write sliced binary bytes, -1 length uses full remaining buffer."""
    require_non_blank(base64_data, "data_base64")
    data = base64.b64decode(base64_data.encode("iso-8859-1"))
    file_write.write_binary_file(file_path, data, 0, len(data), append)
    return {}
