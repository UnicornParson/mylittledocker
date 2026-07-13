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
Directory operation MCP tool module
Provides tools for directory traversal, full directory copy and directory move.
All tools enforce workspace access restriction to limit file system scope.
"""
from typing import Optional

from .._instance import mcp
from ..path_restrict import restrict_workspace
from ..response_helper import response_helper
from ..util import (dir)


@mcp.tool()
@response_helper
@restrict_workspace(path_argument_names=["source_dir"])
async def fs_list_directory(
        source_dir: str,
        recursive: bool,
        only_files: bool,
        file_extension: Optional[str] = ""
) -> dict:
    """Scan directory, return matched absolute path list."""
    res = dir.list_directory(source_dir, recursive, only_files, file_extension)
    return {"paths": res}


@mcp.tool()
@response_helper
@restrict_workspace(path_argument_names=["source_dir", "copy_dest_dir"])
async def fs_copy_directory(
        source_dir: str,
        copy_dest_dir: str,
        overwrite: Optional[bool] = False
) -> dict:
    """Copy full directory tree, overwrite controls existing target cleanup."""
    dir.copy_directory(source_dir, copy_dest_dir, overwrite)
    return {}


@mcp.tool()
@response_helper
@restrict_workspace(path_argument_names=["source_dir", "dest_dir"])
async def fs_move_directory(
        source_dir: str,
        dest_dir: str,
        overwrite: Optional[bool] = False
) -> dict:
    """Move directory, fail if destination exists."""
    dir.move_directory(source_dir, dest_dir, overwrite)
    return {}
