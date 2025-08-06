# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Low-level path helpers."""

from __future__ import annotations

import hashlib
import os
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

from conda.common.compat import on_win
from conda.common.configuration import custom_expandvars
from conda.models.channel import Channel
from platformdirs import user_cache_dir

from . import APP_NAME

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from datetime import datetime
    from typing import Final

#: Site metadata directory. This is the highest priority location.
SITE_TOS_ROOT: Final = "C:/ProgramData/conda/tos" if on_win else "/etc/conda/tos"

#: System metadata directory. Located in the conda installation.
SYSTEM_TOS_ROOT: Final = "$CONDA_ROOT/conda-meta/tos"

#: User metadata directory. Located in the user home directory.
USER_TOS_ROOT: Final = "~/.conda/tos"

#: Environment metadata directory. Located in the current conda environment.
ENV_TOS_ROOT: Final = "$CONDA_PREFIX/conda-meta/tos"

#: Locations safe from conda package updates (system-wide and user directories).
SAFE_TOS_ROOTS: Final = tuple(
    filter(
        None,
        (
            SITE_TOS_ROOT,
            "/var/lib/conda/tos" if not on_win else None,
            "$XDG_CONFIG_HOME/conda/tos",
            "~/.config/conda/tos",
            USER_TOS_ROOT,
            "$CONDATOS",
        ),
    ),
)

#: Locations vulnerable to conda package updates (conda installation and environment).
VULNERABLE_TOS_ROOTS: Final = (
    SYSTEM_TOS_ROOT,  # $CONDA_ROOT/conda-meta/tos
    ENV_TOS_ROOT,  # $CONDA_PREFIX/conda-meta/tos
)

#: Preferred restore locations (safe, in priority order).
RESTORE_PRIORITY: Final = tuple(
    filter(
        None,
        (
            SITE_TOS_ROOT,  # Highest priority, system-wide
            "/var/lib/conda/tos" if not on_win else None,
            USER_TOS_ROOT,  # User-writable fallback
            "$XDG_CONFIG_HOME/conda/tos",
            "~/.config/conda/tos",
        ),
    ),
)

#: Search path for metadata directories.
SEARCH_PATH: Final = tuple(
    filter(
        None,
        (
            SITE_TOS_ROOT,
            "/var/lib/conda/tos" if not on_win else None,
            SYSTEM_TOS_ROOT,
            "$XDG_CONFIG_HOME/conda/tos",
            "~/.config/conda/tos",
            USER_TOS_ROOT,
            ENV_TOS_ROOT,
            # mirrors $CONDARC
            "$CONDATOS",
        ),
    ),
)

#: Metadata file glob pattern.
TOS_GLOB: Final = "*.json"

#: OS and user specific metadata cache directory.
CACHE_DIR: Final = Path(user_cache_dir(APP_NAME, appauthor=APP_NAME))

#: Directory for backup/restore operations.
TOS_BACKUP_DIR: Final = CACHE_DIR / "backup"


@cache
def hash_channel(channel: str | Channel) -> str:
    """Hash the channel to remove problematic characters (e.g. /)."""
    channel = Channel(channel)
    if not channel.base_url:
        raise ValueError(
            "`channel` must have a base URL. "
            "(hint: `conda.models.channel.MultiChannel` cannot be hashed)"
        )

    hasher = hashlib.new("sha256")
    hasher.update(channel.channel_location.encode("utf-8"))
    hasher.update(channel.channel_name.encode("utf-8"))
    return hasher.hexdigest()


def get_location_hash(location: str | Path) -> str:
    """Get a short hash for a location path for backup directory naming."""
    return hashlib.md5(str(location).encode()).hexdigest()[:8]  # noqa: S324


def get_path(path: str | os.PathLike[str] | Path) -> Path:
    """Expand environment variables and user home in the path."""
    if isinstance(path, str):
        path = custom_expandvars(path, os.environ)
    elif not isinstance(path, Path):
        raise TypeError("`path` must be a string or `pathlib.Path`.")
    return Path(path).expanduser()


def get_search_path(
    extend_search_path: Iterable[str | os.PathLike[str] | Path] | None = None,
) -> Iterator[Path]:
    """Get all root metadata paths ordered from highest to lowest priority."""
    seen: set[Path] = set()
    for tos_root in (*SEARCH_PATH, *(extend_search_path or ())):
        if (path := get_path(tos_root)).is_dir() and path not in seen:
            yield path
            seen.add(path)


def get_tos_dir(
    tos_root: str | os.PathLike[str] | Path,
    channel: str | Channel,
) -> Path:
    """Get the metadata directory for the given channel."""
    return get_path(tos_root) / hash_channel(channel)


def get_metadata_path(
    tos_root: str | os.PathLike[str] | Path,
    channel: str | Channel,
    version: datetime,
) -> Path:
    """Get the metadata file path for the given channel and version."""
    return get_tos_dir(tos_root, channel) / f"{version.timestamp()}.json"


def get_all_channel_paths(
    extend_search_path: Iterable[str | os.PathLike[str] | Path] | None = None,
) -> Iterator[Path]:
    """Get all local metadata file paths."""
    for path in get_search_path(extend_search_path):
        yield from sorted(get_path(path).glob(f"*/{TOS_GLOB}"))


def get_channel_paths(
    channel: str | Channel,
    *,
    extend_search_path: Iterable[str | os.PathLike[str] | Path] | None = None,
) -> Iterator[Path]:
    """Get all local metadata file paths for the given channel."""
    for path in get_search_path(extend_search_path):
        yield from sorted(get_tos_dir(path, channel).glob(TOS_GLOB))


def get_cache_path(channel: str | Channel) -> Path:
    """Get the metadata cache file path for the given channel."""
    return CACHE_DIR / f"{hash_channel(channel)}.cache"


def get_cache_paths() -> Iterator[Path]:
    """Get all local metadata cache file paths."""
    yield from sorted(CACHE_DIR.glob("*.cache"))


def is_vulnerable_location(path: str | os.PathLike[str] | Path) -> bool:
    """Check if a path is in a location vulnerable to conda package updates."""
    path_str = str(get_path(path))
    return any(
        str(get_path(vulnerable_root)) in path_str
        for vulnerable_root in VULNERABLE_TOS_ROOTS
    )


def find_best_restore_location() -> Path:
    """Find the highest priority location where we can write for safe restoration."""
    for location in RESTORE_PRIORITY:
        try:
            path = get_path(location)
            # Test if writable by creating and removing a test file
            path.mkdir(parents=True, exist_ok=True)
            test_file = path / ".write_test"
            test_file.touch()
            test_file.unlink()
            return path
        except (PermissionError, OSError):
            continue

    # Fallback to user directory if all else fails
    return get_path(USER_TOS_ROOT)
