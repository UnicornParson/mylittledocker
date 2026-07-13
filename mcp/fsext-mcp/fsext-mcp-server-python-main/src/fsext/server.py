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
fsext-mcp-server - Extended File System MCP Tool Server
Feature-rich filesystem operation toolkit for Model Context Protocol
Supported transport: stdio / sse / streamable-http
"""
import argparse
from pathlib import Path

from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
import uvicorn

from . import path_restrict
from ._instance import mcp
from .tool.fs_dir import (fs_list_directory, fs_copy_directory, fs_move_directory)
from .tool.fs_base import (fs_create_file, fs_delete_file, fs_copy_file,
                           fs_move_file, fs_is_file_exists, fs_get_file_info)
from .tool.fs_read_write import (fs_read_full_text, fs_read_text_range,
                                 fs_read_binary_chunk, fs_write_text, fs_write_binary)
from .tool.fs_search_replace import (fs_search_files_by_content, fs_search_in_files_by_content,
                                     fs_search_in_file_by_content, fs_file_replace)
from .tool.fs_img import (fs_image_crop, fs_image_resize, fs_image_rotate, fs_ocr_extract_text)


def main():
    # CLI argument definition, description & help text
    parser = argparse.ArgumentParser(
        prog="fsext-mcp-server",
        description="fsext-mcp-server | Extended File System Tool Server for MCP protocol",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="Supported transport modes:\n"
               "  stdio: Default, for local MCP client integration (Claude Desktop, Cursor)\n"
               "  sse: Server-Sent Events, lightweight remote connection\n"
               "  http: Official MCP streamable HTTP remote transport"
    )

    parser.add_argument(
        "--transport",
        type=str,
        default="stdio",
        choices=["stdio", "sse", "http"],
        help="MCP transport protocol (host/port ignored under stdio)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Bind host address for sse / streamable-http transport (ignored in stdio mode)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Bind port number for sse / streamable-http transport (ignored in stdio mode)"
    )
    parser.add_argument(
        "--lock-root",
        type=str,
        default=None,
        help="Restrict all file operations inside this root directory; leave empty for full filesystem access"
    )

    args = parser.parse_args()
    args.transport = args.transport.lower()

    # Assign global lock root if provided, pre-validate directory on startup
    lock_path: Path | None = None
    if args.lock_root is not None and args.lock_root.strip():
        raw_lock_str = args.lock_root.strip()
        normalized_lock_str = path_restrict.clean_path(raw_lock_str)
        lock_path = Path(normalized_lock_str).resolve(strict=False)
        from .util.check_utils import require_non_blank, require_writable_directory
        require_non_blank(str(lock_path), "lock-root")
        require_writable_directory(lock_path, "lock-root")
        path_restrict.GLOBAL_LOCK_ROOT = lock_path
        print(f"[LOCK_INIT] Raw input lock-root: {raw_lock_str}")
        print(f"[LOCK_INIT] Normalized global lock root: {path_restrict.GLOBAL_LOCK_ROOT}")

    # Skip console print under stdio to avoid polluting MCP stdout stream
    if args.transport != "stdio":
        print("=" * 64)
        print(f"fsext-mcp-server | Transport: {args.transport}")
        if lock_path is not None:
            print(f"Workspace Lock Root: {lock_path}")
        else:
            print("Workspace Lock Root: Unrestricted (full filesystem access)")
        print(f"Listening on {args.host}:{args.port}")
        print("=" * 64)

    if args.transport != "stdio":
        cors_mw = [
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_methods=["*"],
                allow_headers=["*"],
            )
        ]
        asgi_app = mcp.http_app(
            transport=args.transport,
            stateless_http=True,
            middleware=cors_mw
        )
        uvicorn.run(
            asgi_app,
            host=args.host,
            port=args.port,
            log_level="info"
        )
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
