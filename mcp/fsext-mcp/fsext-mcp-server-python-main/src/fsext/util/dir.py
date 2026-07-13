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
Directory service module providing directory traversal, copy and move utilities.
All methods throw descriptive exceptions for invalid path, permission and input arguments.
"""
import os
import shutil
from pathlib import Path
from typing import List

from .check_utils import (
    require_non_blank,
    require_readable_directory,
    require_writable_parent_directory
)


def list_directory(
        source_dir: str,
        recursive: bool,
        only_files: bool,
        file_extension: str = "",
) -> List[str]:
    """
    Recursively or shallowly scan target directory and return absolute path list of matched entries.

    :param source_dir: Raw string path of target scan directory
    :param recursive: True to traverse all subdirectories recursively; False for shallow scan only
    :param only_files: True to skip directory entries, collect regular files only
    :param file_extension: Case-insensitive file extension filter; blank means no filter
    :return: List of absolute resolved path strings for matched filesystem entries
    :raises ValueError: If source_dir input string is empty or whitespace-only
    :raises IOError: If target directory does not exist or lacks read permission
    """
    require_non_blank(source_dir, "source_dir")
    start_path = Path(source_dir)
    require_readable_directory(start_path, "source_dir")

    ext_raw = file_extension.strip()
    check_extension = bool(ext_raw)
    extension = ext_raw.lower() if check_extension else ""

    paths = []

    if recursive:
        for root, _, file_names in os.walk(start_path):
            root_abs = str(Path(root).resolve())
            if not only_files:
                paths.append(root_abs)

            for fname in file_names:
                if not check_extension or fname.lower().endswith(extension):
                    file_abs = str(Path(root) / fname)
                    paths.append(file_abs)
    else:
        for entry in start_path.iterdir():
            is_file = entry.is_file()
            entry_abs = str(entry.resolve())

            if only_files and not is_file:
                continue

            match = True
            if check_extension and is_file:
                match = entry.name.lower().endswith(extension)

            if match:
                paths.append(entry_abs)

    return paths


def copy_directory(source_dir: str, copy_dest_dir: str, overwrite: bool):
    """
    Copy entire source directory tree to destination path.

    :param source_dir: Source directory raw string path
    :param copy_dest_dir: Target destination directory raw string path
    :param overwrite: True to delete existing destination directory before copy
    :raises ValueError: If source_dir or copy_dest_dir input string is empty/whitespace-only
    :raises IOError: Source dir unreadable, destination parent not writable or not a directory
    """
    require_non_blank(source_dir, "source_dir")
    source = Path(source_dir)
    require_readable_directory(source, "source_dir")

    require_non_blank(copy_dest_dir, "copy_dest_dir")
    target = Path(copy_dest_dir)
    require_writable_parent_directory(target, "copy_dest_dir")

    if overwrite and target.exists():
        shutil.rmtree(target)

    if not target.exists():
        shutil.copytree(source, target)
    else:
        raise IOError(f"Destination directory '{copy_dest_dir}' already exists, overwrite is disabled")


def move_directory(source_dir: str, dest_dir: str, overwrite: bool = False):
    """
    Move entire source directory tree to target destination path.
    Will abort and throw error if destination already exists, no overwriting.

    :param source_dir: Source directory raw string path
    :param dest_dir: Target destination directory raw string path
    :param overwrite: Whether to overwrite existing destination directory, default False
    :raises ValueError: If source_dir or dest_dir input string is empty/whitespace-only
    :raises IOError: Source dir unreadable, destination parent not writable or not a directory
    """
    require_non_blank(source_dir, "source_dir")
    source = Path(source_dir)
    require_readable_directory(source, "source_dir")

    require_non_blank(dest_dir, "dest_dir")
    target = Path(dest_dir)
    require_writable_parent_directory(target, "dest_dir")

    if target.exists():
        if overwrite:
            shutil.rmtree(target)
        else:
            raise IOError(f"Destination path '{dest_dir}' already exists, move aborted")

    shutil.move(source, target)

    if source.exists():
        try:
            shutil.rmtree(source)
        except OSError as e:
            raise IOError(
                f"Move succeeded but failed to delete leftover source directory '{source_dir}': {str(e)}"
            ) from e
