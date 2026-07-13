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
Internal singleton module for FastMCP instance.

This file holds the global unique FastMCP server instance shared across all tool modules.
Prefixed with single underscore to mark as internal private component;
external consumers SHOULD NOT import or rely on this module directly.

Purpose:
1. Eliminate circular import between server entry and tool files
2. Provide unified mcp decorator instance for all MCP tools
3. Avoid TypeError from incorrect @FastMCP.tool() class-level decoration
"""
from fastmcp import FastMCP

# Global single MCP server instance
mcp = FastMCP("fsext-mcp-server")