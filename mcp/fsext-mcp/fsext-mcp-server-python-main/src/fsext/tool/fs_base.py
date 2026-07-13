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
File operation tool collection
Provides all basic single-file manipulation MCP tools, with workspace path access control.
Covers file creation, deletion, metadata query, existence check, copy and move operations.
All tools enforce workspace directory restriction to prevent unauthorized path access.
"""
from typing import Optional

from .._instance import mcp
from ..path_restrict import restrict_workspace
from ..response_helper import response_helper
from ..util import (file)
from .charset import Charset


@mcp.tool()
@response_helper
@restrict_workspace(path_argument_names=["file_path"])
async def fs_create_file(
        file_path: str,
        content: Optional[str] = "",
        charset: Optional[Charset] = Charset.UTF8
) -> dict:
    """Create text file with initial content."""
    file.create_file(file_path, content, charset)
    return {}


@mcp.tool()
@response_helper
@restrict_workspace(path_argument_names=["file_path"])
async def fs_delete_file(
        file_path: str
) -> dict:
    """Delete single regular file, reject directory."""
    file.delete_file(file_path)
    return {}


@mcp.tool()
@response_helper
@restrict_workspace(path_argument_names=["source_file_path", "dest_file_path"])
async def fs_copy_file(
        source_file_path: str,
        dest_file_path: str,
        overwrite: Optional[bool] = False
) -> dict:
    """Copy file with metadata, overwrite toggle."""
    file.copy_file(source_file_path, dest_file_path, overwrite)
    return {}


@mcp.tool()
@response_helper
@restrict_workspace(path_argument_names=["source_file_path", "dest_file_path"])
async def fs_move_file(
        source_file_path: str,
        dest_file_path: str,
        overwrite: Optional[bool] = False
) -> dict:
    """Move file, control overwrite behavior."""
    file.move_file(source_file_path, dest_file_path, overwrite)
    return {}


@mcp.tool()
@response_helper
@restrict_workspace(path_argument_names=["file_path"])
async def fs_get_file_info(
        file_path: str,
        calc_digest: Optional[bool] = False
) -> dict:
    """Get full file/directory metadata."""
    info: file.FileInfo = file.get_file_info(file_path, calc_digest)
    return info._asdict()


@mcp.tool()
@response_helper
@restrict_workspace(path_argument_names=["file_path"])
async def fs_is_file_exists(
        file_path: str
) -> dict:
    """Check filesystem entry existence."""
    exists = file.is_file_exists(file_path)
    return {"exists": exists}
