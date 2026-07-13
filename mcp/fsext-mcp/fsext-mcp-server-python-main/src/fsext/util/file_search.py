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
File content search service, provides directory batch search and single file grep with context lines.
All path arguments are validated via unified check_utils utilities.
"""
import os
import re
from collections import deque
from pathlib import Path
from typing import List, NamedTuple, Optional

from .check_utils import (
    require_non_blank,
    require_readable_file,
    require_readable_directory,
    MAX_INT
)


class FileSearchResult(NamedTuple):
    """
    Represents a search result within a file.
    """
    file_path: str
    start_line: int
    end_line: int
    text: str


def search_files_by_content(
        dir_path: str,
        recursive: bool,
        search_term: str,
        is_regex: bool = False,
        ignore_case: bool = True,
        file_extension: Optional[str] = "",
        charset: Optional[str] = "utf-8",
) -> List[str]:
    """
    Performs a fast content search to find file paths containing the specified search term.

    :param dir_path: The path to the target directory.
    :param recursive: If true, searches subdirectories recursively.
    :param file_extension: The file extension to filter by.
    :param search_term: The text or regular expression to search for.
    :param is_regex: If true, treats the searchTerm as a regular expression.
    :param ignore_case: If true, performs case-insensitive matching.
    :param charset: The character set to use for reading files.
    :return: A list of absolute file paths that contain the search term.
    :raises ValueError: dir_path is blank or target is unreadable directory
    """
    require_non_blank(dir_path, "dir_path")
    start_path = Path(dir_path)
    require_readable_directory(start_path, "dir_path")

    type_filter = file_extension and file_extension.strip()
    query = search_term
    flags = re.IGNORECASE if ignore_case else 0

    res_files = []

    for root, _, files in os.walk(start_path):
        for file in files:
            path = Path(root) / file
            if type_filter and not path.name.lower().endswith(type_filter):
                continue

            try:
                with open(path, "r", encoding=charset, errors="ignore") as f:
                    for line in f:
                        if is_regex:
                            if re.search(query, line, flags):
                                res_files.append(str(path.resolve()))
                                break
                        else:
                            if (ignore_case and query.lower() in line.lower()) or (
                                    not ignore_case and query in line
                            ):
                                res_files.append(str(path.resolve()))
                                break
            except Exception:
                # Ignore files that cannot be read
                pass
        if not recursive:
            break

    return res_files


def search_in_files_by_content(
        dir_path: str,
        recursive: bool,
        search_term: str,
        limit: int,
        is_regex: bool,
        ignore_case: bool,
        lines_before: int,
        lines_after: int,
        file_extension: Optional[str] = "",
        charset: Optional[str] = "utf-8",
) -> List[FileSearchResult]:
    """
    Performs a deep content search across multiple files.

    :param dir_path: The path to the target directory.
    :param recursive: If true, searches subdirectories recursively.
    :param search_term: The text or regular expression to search for.
    :param limit: The maximum number of matching results to process.
    :param is_regex: If true, treats the searchTerm as a regular expression.
    :param ignore_case: If true, performs case-insensitive matching.
    :param lines_before: The number of context lines to include before the matched line.
    :param lines_after: The number of context lines to include after the matched line.
    :param file_extension: The file extension to filter by.
    :param charset: The character set to use for reading files.
    :return: A list of FileSearchResult objects.
    :raises ValueError: dir_path blank, unreadable dir, limit<=0, lines_before/lines_after negative
    """
    require_non_blank(dir_path, "dir_path")
    start_path = Path(dir_path)
    require_readable_directory(start_path, "dir_path")

    if lines_before < 0 or lines_after < 0:
        raise ValueError("lines_before and lines_after must be non-negative")
    if limit <= 0:
        raise ValueError("limit must be larger than 0")

    type_suffix = file_extension.strip().lower() if file_extension else None
    flags = re.IGNORECASE if ignore_case else 0
    pattern = re.compile(search_term, flags) if is_regex else None

    results: List[FileSearchResult] = []

    for root, dirs, files in os.walk(start_path):
        if len(results) >= limit:
            return results

        if not recursive:
            dirs.clear()

        for file in files:
            if len(results) >= limit:
                return results

            path = Path(root) / file

            if type_suffix and not path.name.lower().endswith(type_suffix):
                continue

            _grep_file(
                path, results, pattern, search_term, ignore_case,
                limit, lines_before, lines_after, charset
            )

    return results


def search_in_file_by_content(
        file_path: str,
        search_term: str,
        is_regex: bool,
        ignore_case: bool,
        lines_before: int,
        lines_after: int,
        charset: Optional[str] = "utf-8",
) -> List[FileSearchResult]:
    """
    Performs a content search in the specified file.

    :param file_path: The path to the target file.
    :param search_term: The text or regular expression to search for.
    :param is_regex: If true, treats the searchTerm as a regular expression.
    :param ignore_case: If true, performs case-insensitive matching.
    :param lines_before: The number of context lines to include before the matched line.
    :param lines_after: The number of context lines to include after the matched line.
    :param charset: The character set to use for reading files.
    :return: A list of FileSearchResult objects.
    :raises ValueError: file_path blank, unreadable file, lines_before/lines_after negative
    """
    require_non_blank(file_path, "file_path")
    path = Path(file_path)
    require_readable_file(path, "file_path")
    if lines_before < 0 or lines_after < 0:
        raise ValueError("lines_before and lines_after must be non-negative")

    flags = re.IGNORECASE if ignore_case else 0
    pattern = re.compile(search_term, flags) if is_regex else None

    results = []
    _grep_file(
        path,
        results,
        pattern,
        search_term,
        ignore_case,
        MAX_INT,
        lines_before,
        lines_after,
        charset,
    )
    return results


def _grep_file(
        path: Path,
        results: List[FileSearchResult],
        pattern: Optional[re.Pattern],
        search_term: str,
        ignore_case: bool,
        limit: int,
        lines_before: int,
        lines_after: int,
        charset: Optional[str] = "utf-8",
):
    """
    Internal line stream processor, maintains sliding window buffer for context lines.
    Merge continuous matched lines into single context block, flush buffer after after-lines consumed.
    Exit early if global result list hits limit.
    """
    search_term = search_term.lower() if ignore_case else search_term

    line_stack: deque = deque()
    search_hit = False
    count_after = 0
    line_no = 0

    with open(path, "r", encoding=charset) as f:
        for line in f:
            line = line.rstrip('\n\r')
            line_no += 1

            if len(results) >= limit:
                return

            # Match logic branch
            if pattern:
                is_match = bool(pattern.search(line))
            else:
                if ignore_case:
                    is_match = search_term in line.lower()
                else:
                    is_match = search_term in line

            if is_match:
                line_stack.append(line)
                search_hit = True
                count_after = 0
            elif search_hit:
                # Post-match context collection stage

                # When lineAfter equals 0 and countAfter reaches lineAfter threshold, and if
                # linesBefore is non-zero, push current line into result set then store to stack
                if count_after == lines_after or count_after + 1 == lines_after:
                    l_no: int
                    line_fed = False
                    if count_after == lines_after:
                        # Current line belongs to next context group, skip to append
                        l_no = line_no - 1
                    else:
                        line_stack.append(line)
                        line_fed = True
                        l_no = line_no

                    start_line = l_no - len(line_stack) + 1
                    context = "\n".join(line_stack)
                    results.append(FileSearchResult(
                        str(path.resolve()),
                        start_line,
                        l_no,
                        context
                    ))

                    # Reset context state for next match group
                    search_hit = False
                    count_after = 0
                    line_stack.clear()

                    # Preserve current line as pre-context for subsequent matches
                    if not line_fed and lines_before > 0:
                        line_stack.append(line)
                else:
                    line_stack.append(line)
                    count_after += 1
            else:
                # Maintain pre-match sliding context window
                line_stack.append(line)
                if lines_before == 0:
                    line_stack.clear()
                elif len(line_stack) > lines_before:
                    line_stack.popleft()

    # Flush remaining matched context buffer when file reaches EOF
    if search_hit and line_stack:
        start_line = line_no - len(line_stack) + 1
        context = "\n".join(line_stack)
        results.append(FileSearchResult(
            str(path.resolve()),
            start_line,
            line_no,
            context
        ))
