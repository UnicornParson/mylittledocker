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
Service for performing search and replace operations on text files.
Uses temporary file + atomic replace to avoid original file corruption during rewrite.
"""
import os
import tempfile
from pathlib import Path

from .check_utils import (
    require_non_blank,
    require_readable_file
)


def file_replace(
        file_path: str, search_term: str, replacement: str, line_separator: str = "\n"
) -> int:
    """
    Execute in-place search & replace on target text file with atomic safe write.
    Creates temp file in same directory then swaps to original file to prevent data loss.

    :param file_path: String path of target text file
    :param search_term: Substring to match and replace
    :param replacement: Substitution string for matched content
    :param line_separator: Suffix appended if processed line lacks line break
    :return: Count of lines that contained at least one matched & replaced substring
    :raises ValueError: file_path is blank, or target is not a readable regular file
    """
    require_non_blank(file_path, "file_path")
    src_path = Path(file_path)
    require_readable_file(src_path, "file_path")

    replace_count = 0

    # Temp file shares parent directory to guarantee atomic os.replace cross-platform
    fd, tmp_path_str = tempfile.mkstemp(suffix=".tmp", dir=src_path.parent)
    tmp_path = Path(tmp_path_str)

    try:
        with open(src_path, "r") as reader, os.fdopen(fd, "w") as writer:
            for line in reader:
                new_line = line.replace(search_term, replacement)
                if new_line != line:
                    replace_count += 1
                writer.write(new_line)
                if not new_line.endswith(line_separator):
                    writer.write(line_separator)

        # Atomic overwrite, replace is cross-platform safe rename operation
        os.replace(tmp_path, src_path)
    except Exception as e:
        # Cleanup orphan temp file on any failure
        if tmp_path.exists():
            tmp_path.unlink()
        raise e

    return replace_count
