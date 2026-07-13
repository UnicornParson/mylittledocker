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
import os
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


def resolve_workspace_path(target_path: str, lock_root: Path) -> Path:
    """
    Normalize and resolve a target path relative to the workspace lock root.
    Treats the workspace root as the filesystem root for all paths:
      - '/test/file.txt'       -> lock_root / 'test/file.txt'
      - 'test/file.txt'        -> lock_root / 'test/file.txt'
      - '/workspace/file.txt'  -> lock_root / 'file.txt'  (or returned as-is if matches)
      - '/../etc/passwd'       -> raises WorkspaceEscapeError (traversal)
      - 'test/../../etc'       -> raises WorkspaceEscapeError (traversal)

    The function:
      1. Cleans the path (backslashes, double slashes, whitespace)
      2. If the path starts with '/', checks whether it already points inside
         lock_root. If so, uses it as-is (avoids duplicating lock_root prefix).
      3. Otherwise strips leading slash and joins with lock_root.
      4. Resolves '..' components via normpath, then resolves symlinks.
      5. Verifies the result stays inside lock_root via relative_to.

    Args:
        target_path: Raw path from MCP tool input (may be absolute or relative)
        lock_root: Resolved workspace root directory assigned at startup

    Returns:
        Resolved absolute Path guaranteed to be inside lock_root

    Raises:
        WorkspaceEscapeError: If the resolved path escapes the workspace
    """
    require_non_blank(target_path, "target_path")

    # Step 1: basic cleanup (backslashes, double slashes, whitespace)
    cleaned = clean_path(target_path)

    # Step 2: if path starts with '/', check whether it already lives under lock_root
    # Direct check using the raw cleaned path (no double-joining)
    if cleaned.startswith("/"):
        candidate = Path(cleaned).resolve(strict=False)
        try:
            candidate.relative_to(lock_root)
            # Path is already inside workspace — return as-is
            return candidate
        except ValueError:
            pass
        # Path starts with '/' but is NOT inside lock_root:
        # strip leading slash and treat as relative to lock_root
        cleaned = cleaned.lstrip("/")

    # Step 3: normalize '..' components safely (no symlink resolve yet)
    normalized = Path(os.path.normpath(cleaned))

    # Step 4: join with lock_root and fully resolve (includes symlinks)
    joined = (lock_root / normalized).resolve(strict=False)

    # Step 5: verify the resolved path is strictly inside lock_root
    try:
        joined.relative_to(lock_root)
    except ValueError:
        raise WorkspaceEscapeError(
            f"Path `{target_path}` escapes workspace `{lock_root}`"
        )

    return joined


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

    try:
        resolve_workspace_path(target_path, lock_root_path)
        return True
    except WorkspaceEscapeError:
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

            for arg_name in path_argument_names:
                target_value = kwargs.get(arg_name)
                if target_value is None:
                    continue

                # Resolve path relative to workspace root and replace it
                resolved = resolve_workspace_path(target_value, GLOBAL_LOCK_ROOT)
                kwargs[arg_name] = str(resolved)
                logger.debug(
                    f"Path '{arg_name}' resolved: '{target_value}' -> '{resolved}'"
                )

            return await async_tool_func(**kwargs)

        return wrapper

    return decorator
