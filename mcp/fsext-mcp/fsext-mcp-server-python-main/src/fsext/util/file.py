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
General file utility service, provides metadata query, file create/delete/copy/move operations.
All path input validation uses unified check_utils utilities.
"""
import os
import shutil
import hashlib
from pathlib import Path
from typing import NamedTuple

from .check_utils import (
    require_non_blank,
    require_path_exists,
    require_readable_file,
    require_writable_parent_directory
)


class FileInfo(NamedTuple):
    """
    Metadata container for file or directory attributes.
    """
    absolute_path: str
    is_readable: bool
    is_writable: bool
    size: int
    is_regular_file: bool
    is_directory: bool
    is_symbolic_link: bool
    creation_millis: float
    last_modified_millis: float
    last_access_millis: float
    sha256_digest: str


def get_file_hash_digest(file_path: str) -> str:
    """
    Generates a SHA-256 hash digest of a file at the given path.
    :param file_path: Path to the target file.
    :return: Lowercase hex string of sha256 digest
    """
    file_p = Path(file_path)
    sha256 = hashlib.sha256()

    chunk_size = 65536
    with open(file_p, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)

    return sha256.hexdigest()


def create_file(file_path: str, content: str = "", charset: str = "utf-8"):
    """
    Create text file with given content, strict empty parameter guard.
    :param file_path: Target absolute/relative file path string
    :param content: Initial text content to write into new file
    :param charset: Text file decode encoding
    :raises ValueError: If file_path is empty string or whitespace only
    """
    # Empty parameter validation
    require_non_blank(file_path, "file_path")
    path = Path(file_path)
    require_writable_parent_directory(path, "file_path")

    target = Path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding=charset)


def delete_file(file_path: str):
    """
    Permanently remove a single regular file from disk.
    Directory deletion is unsupported.
    Validation sequence: blank check → file exists & readable → parent dir writable.
    File delete permission depends on parent folder write access instead of file write flag.
    :param file_path: Absolute or relative path of target file
    :raises ValueError: Blank input path
    :raises FileNotFoundError: File not found
    :raises IsADirectoryError: Path points to folder
    :raises PermissionError: No read on file / no write on parent directory
    """
    require_non_blank(file_path, "filePath")
    path = Path(file_path)
    require_readable_file(path, "filePath")
    require_writable_parent_directory(path, "filePath")

    os.unlink(file_path)


def get_file_info(file_path: str, calc_digest: bool) -> FileInfo:
    """
    Retrieves full metadata information of target file or directory.

    :param file_path: The path to the target file or directory.
    :param calc_digest: If calculate hash digest for the given file.
    :return: A FileInfo record containing the file's metadata.
    :raises ValueError: file_path is blank string, target path does not exist
    """
    require_non_blank(file_path, "file_path")
    path = Path(file_path)
    require_path_exists(path, "file_path")

    stat = path.stat()

    return FileInfo(
        absolute_path=str(path.resolve()),
        is_readable=os.access(path, os.R_OK),
        is_writable=os.access(path, os.W_OK),
        size=stat.st_size,
        is_regular_file=path.is_file(),
        is_directory=path.is_dir(),
        is_symbolic_link=path.is_symlink(),
        creation_millis=stat.st_ctime * 1000,
        last_modified_millis=stat.st_mtime * 1000,
        last_access_millis=stat.st_atime * 1000,
        sha256_digest=get_file_hash_digest(file_path) if calc_digest else ''
    )


def get_file_extension(filename: str, name: str) -> str:
    """
    Extract trailing file extension without leading dot from filename.

    :param filename: The name of the file.
    :param name: The parameter name used in exception message.
    :return: Suffix string after last dot, no leading dot.
    :raises ValueError: filename blank, or filename contains no dot separator
    """
    require_non_blank(filename, name)
    if "." in filename:
        return filename.rsplit(".", 1)[1]
    else:
        raise ValueError(f"Cannot get the extension of the {name}")


def is_file_exists(filename: str) -> bool:
    """
    Check if target filesystem entry exists.

    :param filename: Path-like target to check existence.
    :return: True if entry exists, False otherwise.
    """
    require_non_blank(filename, "filename")
    return filename is not None and os.path.exists(filename)


def copy_file(source_file_path: str, dest_file_path: str, overwrite: bool):
    """
    Copy file with full metadata preservation via shutil.copy2.

    :param source_file_path: The path to the source file.
    :param dest_file_path: The path to the destination file.
    :param overwrite: If true, overwrite destination if already exists.
    """
    _do_file(shutil.copy2, source_file_path, dest_file_path, overwrite)


def move_file(source_file_path: str, dest_file_path: str, overwrite: bool):
    """
    Move file to target destination, supports overwrite control.

    :param source_file_path: The path to the source file.
    :param dest_file_path: The path to the destination file.
    :param overwrite: If true, overwrite destination if already exists.
    """
    _do_file(shutil.move, source_file_path, dest_file_path, overwrite)


def _do_file(operation, source_file_path: str, dest_file_path: str, overwrite: bool):
    """
    Internal shared logic for copy/move file, unify validation and overwrite check.
    """
    require_non_blank(source_file_path, "source_file_path")
    source = Path(source_file_path)
    require_readable_file(source, "source_file_path")

    require_non_blank(dest_file_path, "dest_file_path")
    target = Path(dest_file_path)
    require_writable_parent_directory(target, "dest_file_path")

    if not overwrite and target.exists():
        raise FileExistsError(f"Destination file {target} already exists.")

    operation(str(source), str(target))
