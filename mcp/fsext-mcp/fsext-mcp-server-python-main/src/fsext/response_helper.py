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
Standard MCP response serialization utility
Produce uniform JSON string assigned directly to RPC top-level "result" field
Schema specification:
{
  "res": {
    "success": boolean,
    "info": object
  }
}
- success=true: info = raw documented tool return payload
- success=false: info = {"code": error_code, "message": brief_error_desc}
"""
import logging
from functools import wraps
from typing import Callable

from .tool_error import WorkspaceEscapeError

logger = logging.getLogger("fsext.tool")


def build_response(success: bool, info: dict) -> dict:
    """
    Generate standardized unified response dict for MCP tool return
    :param success: operation overall status flag
    :param info: raw business data on success; {code, message} dict on failure
    :return: standardized response dict
    """
    payload = {
        "res": {
            "success": success,
            "info": info
        }
    }
    # return json.dumps(payload, ensure_ascii=False)
    return payload


def response_helper(func: Callable) -> Callable:
    """
    Async decorator for MCP file system tools:
    - Catch workspace sandbox, validation, permission, IO & unhandled errors
    - Wrap raw business output to unified MCP response dict
    - Log full stack trace internally, expose minimal clean error to client
    """

    @wraps(func)
    async def wrapper(**kwargs) -> dict:
        try:
            raw_output = await func(**kwargs)
            return build_response(success=True, info=raw_output)

        # Workspace sandbox restriction
        except WorkspaceEscapeError as err:
            msg = str(err)
            logger.warning(f"[TOOL:{getattr(func, '__name__', repr(func))}] Workspace escape blocked: {msg}",
                           exc_info=False)
            return build_response(
                success=False,
                info={
                    "code": "WORKSPACE_ESCAPE_FORBIDDEN",
                    "message": msg
                }
            )

        # Input & path validation error
        except ValueError as err:
            msg = str(err)
            logger.warning(f"[TOOL:{getattr(func, '__name__', repr(func))}] Parameter validation failed: {msg}",
                           exc_info=True)
            return build_response(
                success=False,
                info={
                    "code": "VALIDATION_ERROR",
                    "message": msg
                }
            )

        # File access permission denied
        except PermissionError as err:
            msg = f"Permission denied: {err}"
            logger.warning(f"[TOOL:{getattr(func, '__name__', repr(func))}] Access forbidden: {msg}", exc_info=True)
            return build_response(
                success=False,
                info={
                    "code": "PERMISSION_DENIED",
                    "message": msg
                }
            )

        # General filesystem IO error
        except OSError as err:
            msg = f"File system operation failed: {err}"
            logger.error(f"[TOOL:{getattr(func, '__name__', repr(func))}] IO exception: {msg}", exc_info=True)
            return build_response(
                success=False,
                info={
                    "code": "IO_ERROR",
                    "message": msg
                }
            )

        # Uncaught runtime error
        except Exception as err:
            err_cls = type(err).__name__
            msg = f"Internal runtime error: {err_cls}"
            logger.error(f"[TOOL:{getattr(func, '__name__', repr(func))}] Unhandled exception", exc_info=True)
            return build_response(
                success=False,
                info={
                    "code": "INTERNAL_ERROR",
                    "message": msg
                }
            )

    return wrapper
