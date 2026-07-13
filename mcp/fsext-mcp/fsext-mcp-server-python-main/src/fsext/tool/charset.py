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
Standard text encoding identifiers for file read/write operations.
"""
from enum import Enum


class Charset(str, Enum):
    """
    Standard text encoding identifiers for file read/write operations.
    Used to control byte <-> string conversion when persisting text content to disk.
    """
    UTF8 = "utf-8"
    """Universal UTF-8 encoding, default for most plain text files."""

    UTF16 = "utf-16"
    """UTF-16 wide character encoding, common for Windows Unicode documents."""

    LATIN1 = "latin-1"
    """ISO-8859-1, 1:1 byte mapping without character substitution."""

    ISO_8859_1 = "iso-8859-1"
    """Identical mapping to latin-1, alternative standard name for ISO-8859-1 encoding."""

    CP1252 = "cp1252"
    """Windows-1252 superset of ISO-8859-1, adds extra printable punctuation used in Western European Windows files."""

    WINDOWS_1252 = "Windows-1252"
    """String alias identical to cp1252, human-readable name for Windows ANSI encoding."""

    GBK = "gbk"
    """Mainland Chinese Windows legacy encoding, covers Simplified Chinese characters."""

    GB2312 = "gb2312"
    """Older simplified Chinese standard encoding, subset of GBK."""

    SHIFT_JIS = "shift_jis"
    """Legacy Japanese encoding widely used on Windows and Japanese desktop software."""

    EUC_JP = "euc_jp"
    """Extended Unix Code encoding for Japanese text, common on Linux/Unix systems."""

    EUC_KR = "euc_kr"
    """Extended Unix Code encoding for Korean Hangul text."""
