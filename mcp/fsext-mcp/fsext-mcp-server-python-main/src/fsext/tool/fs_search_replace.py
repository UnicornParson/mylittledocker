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
File search and text replace MCP tool module Provides directory/file content search
with regex support and contextual preview, plus in-place text replacement for single
files. All directory and file paths are restricted within allowed workspace.
"""
from typing import Optional

from .._instance import mcp
from ..path_restrict import restrict_workspace
from ..response_helper import response_helper
from ..util import (file_search, file_replace)
from .charset import Charset


@mcp.tool()
@response_helper
@restrict_workspace(path_argument_names=["dir_path"])
async def fs_search_files_by_content(
        dir_path: str,
        recursive: bool,
        search_term: str,
        is_regex: Optional[bool] = False,
        ignore_case: Optional[bool] = True,
        file_extension: Optional[str] = "",
        charset: Optional[Charset] = Charset.UTF8
) -> dict:
    """Search dir, return paths of files containing target text."""
    paths = file_search.search_files_by_content(dir_path, recursive, search_term,
                                                is_regex, ignore_case, file_extension, charset)
    return {"paths": paths}


@mcp.tool()
@response_helper
@restrict_workspace(path_argument_names=["dir_path"])
async def fs_search_in_files_by_content(
        dir_path: str,
        recursive: bool,
        search_term: str,
        limit: int,
        is_regex: Optional[bool] = False,
        ignore_case: Optional[bool] = True,
        lines_before: Optional[int] = 0,
        lines_after: Optional[int] = 0,
        file_extension: Optional[str] = "",
        charset: Optional[Charset] = Charset.UTF8
) -> dict:
    """Search multi-file with line context, return matched blocks."""
    res_list = file_search.search_in_files_by_content(dir_path, recursive, search_term,
                                                      limit, is_regex, ignore_case,
                                                      lines_before, lines_after, file_extension, charset)
    results = [item._asdict() for item in res_list]
    return {"results": results}


@mcp.tool()
@response_helper
@restrict_workspace(path_argument_names=["file_path"])
async def fs_search_in_file_by_content(
        file_path: str,
        search_term: str,
        is_regex: Optional[bool] = False,
        ignore_case: Optional[bool] = True,
        lines_before: Optional[int] = 0,
        lines_after: Optional[int] = 0,
        charset: Optional[Charset] = Charset.UTF8
) -> dict:
    """Single file content search with line context."""
    res_list = file_search.search_in_file_by_content(file_path, search_term, is_regex, ignore_case,
                                                     lines_before, lines_after, charset)
    results = [item._asdict() for item in res_list]
    return {"results": results}


@mcp.tool()
@response_helper
@restrict_workspace(path_argument_names=["file_path"])
async def fs_file_replace(
        file_path: str,
        search_term: str,
        replacement: str,
        line_separator: Optional[str] = "\n"
) -> dict:
    """In-place text replace, return matched line count."""
    count = file_replace.file_replace(file_path, search_term, replacement, line_separator)
    return {"count": count}
