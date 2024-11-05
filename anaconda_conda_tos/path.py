# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS path functions."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import TYPE_CHECKING

from conda.common.compat import on_win
from conda.common.configuration import custom_expandvars
from conda.models.channel import Channel

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from typing import Final

SITE_TOS_ROOT: Final = "C:/ProgramData/conda/tos" if on_win else "/etc/conda/tos"

# mirrors conda.base.context.sys_rc_path
SYSTEM_TOS_ROOT: Final = "$CONDA_ROOT/conda-meta/tos"

# mirrors conda.base.context.user_rc_path
USER_TOS_ROOT: Final = "~/.conda/tos"

ENV_TOS_ROOT: Final = "$CONDA_PREFIX/conda-meta/tos"

# mirrors conda.base.constants.SEARCH_PATH locations
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

TOS_GLOB: Final = "*.json"


def hash_channel(channel: str | Channel) -> str:
    """Hash the channel to remove problematic characters (e.g. /)."""
    channel = Channel(channel)
    if not channel.base_url:
        raise ValueError("Channel must have a base URL. MultiChannel cannot be hashed.")

    hasher = hashlib.new("sha256")
    hasher.update(channel.channel_location.encode("utf-8"))
    hasher.update(channel.channel_name.encode("utf-8"))
    return hasher.hexdigest()


def get_path(path: str | os.PathLike[str] | Path) -> Path:
    """Expand environment variables and user home in the path."""
    if isinstance(path, str):
        path = custom_expandvars(path, os.environ)
    return Path(path).expanduser()


def get_search_path(
    extend_search_path: Iterable[str | os.PathLike[str] | Path] | None = None,
) -> Iterator[Path]:
    """Get all root ToS directories."""
    seen: set[Path] = set()
    for tos_root in (*SEARCH_PATH, *(extend_search_path or ())):
        if (path := get_path(tos_root)).is_dir() and path not in seen:
            yield path
            seen.add(path)


def get_tos_dir(
    tos_root: str | os.PathLike[str] | Path,
    channel: str | Channel,
) -> Path:
    """Get the ToS directory for the given channel."""
    return get_path(tos_root) / hash_channel(channel)


def get_metadata_path(
    tos_root: str | os.PathLike[str] | Path,
    channel: str | Channel,
    version: int,
) -> Path:
    """Get the ToS file path for the given channel and version."""
    return get_tos_dir(tos_root, channel) / f"{version}.json"


def get_all_channel_paths(
    extend_search_path: Iterable[str | os.PathLike[str] | Path] | None = None,
) -> Iterator[Path]:
    """Get all local ToS file paths."""
    for path in get_search_path(extend_search_path):
        yield from get_path(path).glob(f"*/{TOS_GLOB}")


def get_channel_paths(
    channel: str | Channel,
    *,
    extend_search_path: Iterable[str | os.PathLike[str] | Path] | None = None,
) -> Iterator[Path]:
    """Get all local ToS file paths for the given channel."""
    for path in get_search_path(extend_search_path):
        yield from get_tos_dir(path, channel).glob(TOS_GLOB)
