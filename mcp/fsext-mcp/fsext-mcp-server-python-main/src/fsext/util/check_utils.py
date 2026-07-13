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
Utility class for performing various checks.
All validation functions raise ValueError when check condition fails.
"""
import os
from pathlib import Path
from typing import Union

PathLike = Union[str, bytes, os.PathLike, Path]

MAX_INT = 2147483647


def require_non_blank(s: str, name: str):
    """
    Validates that the given string is not None and not blank.

    :param s: the string to validate
    :param name: the name of the parameter (used in exception message)
    :raises ValueError: if the string is None or blank
    """
    if s is None or not s.strip():
        raise ValueError(f"Parameter '{name}' cannot be empty")


def require_path_exists(path: Path, name: str):
    """
    Validates that the given Path object exists on filesystem.

    :param path: the Path to validate
    :param name: the name of the parameter (used in exception message)
    :raises ValueError: if path is None or the target does not exist
    """
    if path is None:
        raise ValueError(f"Parameter '{name}' cannot be None")
    if not path.exists():
        raise ValueError(f"Parameter '{name}'({path}) does not exist")


def require_file_exists(file: os.PathLike, name: str):
    """
    Validates that the given path-like target exists and is a regular file.

    :param file: the path-like file target to validate
    :param name: the name of the parameter (used in exception message)
    :raises ValueError: if file is None, target missing or not a regular file
    """
    if file is None:
        raise ValueError(f"Parameter '{name}' cannot be None")
    p = Path(file)
    if not p.exists():
        raise ValueError(f"Parameter '{name}'({file}) does not exist")
    if not p.is_file():
        raise ValueError(f"Parameter '{name}'({file}) is not a regular file")


def require_readable_file(path: Path, name: str):
    """
    Validates that Path is non-null, exists, is a regular file and has read permission.

    :param path: the Path to validate
    :param name: the name of the parameter (used in exception message)
    :raises ValueError: if path is None, missing, not a file or unreadable
    """
    if path is None:
        raise ValueError(f"Parameter '{name}' cannot be None")
    if not path.exists():
        raise ValueError(f"Parameter '{name}'({path}) does not exist")
    if not path.is_file():
        raise ValueError(f"Parameter '{name}'({path}) is not a regular file")
    if not os.access(path, os.R_OK):
        raise ValueError(f"Parameter '{name}'({path}) lacks read permission")


def require_writable_file(path: Path, name: str):
    """
    Validates that Path is non-null, exists, is a regular file and has write permission.

    :param path: the Path to validate
    :param name: the name of the parameter (used in exception message)
    :raises ValueError: if path is None, missing, not a file or unwritable
    """
    if path is None:
        raise ValueError(f"Parameter '{name}' cannot be None")
    if not path.exists():
        raise ValueError(f"Parameter '{name}'({path}) does not exist")
    if not path.is_file():
        raise ValueError(f"Parameter '{name}'({path}) is not a regular file")
    if not os.access(path, os.W_OK):
        raise ValueError(f"Parameter '{name}'({path}) lacks write permission")


def require_readable_directory(path: Path, name: str):
    """
    Validates that Path is non-null, exists, is a directory and has read permission.

    :param path: the Path to validate
    :param name: the name of the parameter (used in exception message)
    :raises ValueError: if path is None, missing, not a directory or unreadable
    """
    if path is None:
        raise ValueError(f"Parameter '{name}' cannot be None")
    if not path.exists():
        raise ValueError(f"Parameter '{name}'({path}) does not exist")
    if not path.is_dir():
        raise ValueError(f"Parameter '{name}'({path}) is not a directory")
    if not os.access(path, os.R_OK):
        raise ValueError(f"Parameter '{name}'({path}) lacks read permission")


def require_writable_directory(path: Path, name: str):
    """
    Validates that Path is non-null, exists, is a directory and has write permission.

    :param path: the Path to validate
    :param name: the name of the parameter (used in exception message)
    :raises ValueError: if path is None, missing, not a directory or unwritable
    """
    if path is None:
        raise ValueError(f"Parameter '{name}' cannot be None")
    if not path.exists():
        raise ValueError(f"Parameter '{name}'({path}) does not exist")
    if not path.is_dir():
        raise ValueError(f"Parameter '{name}'({path}) is not a directory")
    if not os.access(path, os.W_OK):
        raise ValueError(f"Parameter '{name}'({path}) lacks write permission")


def require_writable_parent_directory(path: Path, name: str):
    """
    Validates parent directory of target Path exists and has write permission.
    Used for pre-check before creating new file under target path.

    :param path: the Path whose parent directory will be validated
    :param name: the name of the parameter (used in exception message)
    :raises ValueError: if path is None, parent missing, parent not dir or unwritable
    """
    if path is None:
        raise ValueError(f"Parameter '{name}' cannot be None")
    parent_dir = path.parent
    if not parent_dir.exists():
        raise ValueError(f"Parent directory of {name}({path}) does not exist")
    if not parent_dir.is_dir():
        raise ValueError(f"Parent of {name}({path}) is not a valid directory")
    if not os.access(parent_dir, os.W_OK):
        raise ValueError(f"The parent directory of {name}({path}) is not writable")
