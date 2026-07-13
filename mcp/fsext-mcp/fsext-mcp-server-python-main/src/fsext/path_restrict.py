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
Global restricted workspace root, assigned at server startup
"""
from functools import wraps
from pathlib import Path
from typing import List, Optional

from .tool_error import WorkspaceEscapeError
from .response_helper import logger
from .util.check_utils import require_non_blank, require_writable_directory

# Global restricted workspace root, assigned at server startup
GLOBAL_LOCK_ROOT: Optional[Path] = None


def clean_path(raw_path: str) -> str:
    """
    Normalize Windows file path:
    1. Strip leading/trailing whitespace
    2. Replace backslash with forward slash
    3. Remove redundant consecutive separators
    """
    if not raw_path:
        return ""
    stripped = raw_path.strip()
    unix_style = stripped.replace("\\", "/")
    while "//" in unix_style:
        unix_style = unix_style.replace("//", "/")
    return unix_style

def folder_lock_check(lock_root: str, target_path: str) -> bool:
    """
    Verify target path is strictly inside restricted lock root directory.
    Resolve symlinks & normalize paths to prevent path traversal escape.

    Args:
        lock_root: Root workspace directory enforced by server startup arg
        target_path: File/directory path from MCP tool input to validate

    Returns:
        True if target is within lock root subtree; False if out of bounds
    """
    # Validate input string is non-empty and lock dir is writable
    require_non_blank(lock_root, "lock_root")
    lock_root_path = Path(lock_root)
    require_writable_directory(lock_root_path, "lock_root")
    require_non_blank(target_path, "target_path")

    root_real = lock_root_path.resolve(strict=False)
    target_real = Path(target_path).resolve(strict=False)

    try:
        # Native path subtree check, blocks partial prefix matching bypass
        target_real.relative_to(root_real)
        return True
    except ValueError:
        return False


def restrict_workspace(path_argument_names: List[str]):
    """
    Decorator for FastMCP async tools to auto validate all file/dir input paths.
    Skips all validation automatically if GLOBAL_LOCK_ROOT is None (unrestricted mode).
    Throws standardized ToolError to block cross-workspace access.

    Args:
        path_argument_names: List of tool param names that carry file/directory paths
    """

    def decorator(async_tool_func):
        @wraps(async_tool_func)
        async def wrapper(**kwargs):
            if GLOBAL_LOCK_ROOT is None:
                return await async_tool_func(**kwargs)

            lock_root_str = str(GLOBAL_LOCK_ROOT)
            for arg_name in path_argument_names:
                target_value = kwargs.get(arg_name)
                if target_value is None:
                    continue

                if not folder_lock_check(lock_root_str, target_value):
                    err_msg = (
                        f"Access restricted: Path `{target_value}` "
                        f"is outside allowed workspace `{lock_root_str}`"
                    )
                    logger.warning(f"Block cross workspace access: {err_msg}")
                    raise WorkspaceEscapeError(err_msg)
            return await async_tool_func(**kwargs)

        return wrapper

    return decorator
