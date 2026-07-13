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
Custom business exception for all MCP filesystem tool restrictions.
Raised by restrict_workspace decorator when path escapes workspace sandbox.
Caught by mcp_tool_wrapper to return standardized workspace forbidden error.
"""


class FsextToolError(Exception):
    """Base parent exception for all custom file system tool business errors"""
    pass


class WorkspaceEscapeError(FsextToolError):
    """
    Security restriction blocked: target path escapes locked workspace root.
    Triggered by @restrict_workspace sandbox path validation.
    """
    pass
