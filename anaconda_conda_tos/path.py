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
    from typing import Final, Iterator

# mirrors conda.base.context.sys_rc_path
SYSTEM_TOS_ROOT: Final[str] = "$CONDA_ROOT/conda-meta/tos"

# mirrors conda.base.context.user_rc_path
USER_TOS_ROOT: Final[str] = "~/.conda/tos"

# mirrors conda.base.constants.SEARCH_PATH locations
SEARCH_PATH: Final[tuple[str, ...]] = tuple(
    filter(
        None,
        (
            "C:/ProgramData/conda/tos" if on_win else None,
            "/etc/conda/tos" if not on_win else None,
            "/var/lib/conda/tos" if not on_win else None,
            SYSTEM_TOS_ROOT,
            "$XDG_CONFIG_HOME/conda/tos",
            "~/.config/conda/tos",
            USER_TOS_ROOT,
            "$CONDA_PREFIX/conda-meta/tos",
            # mirrors $CONDARC
            "$CONDATOS",
        ),
    ),
)


def hash_channel(channel: str | Channel) -> str:
    """Hash the channel to remove problematic characters (e.g. /)."""
    channel = Channel(channel)
    if not channel.base_url:
        raise ValueError("Channel must have a base URL. MultiChannel cannot be hashed.")

    hasher = hashlib.new("sha256")
    hasher.update(channel.channel_location.encode("utf-8"))
    hasher.update(channel.channel_name.encode("utf-8"))
    return hasher.hexdigest()


def get_tos_root(path: str | os.PathLike[str] | Path) -> Path:
    """Get the root ToS directory."""
    if isinstance(path, str):
        path = custom_expandvars(path, os.environ)
    return Path(path).expanduser()


def get_tos_search_path() -> Iterator[Path]:
    """Get all root ToS directories."""
    for search_path in SEARCH_PATH:
        if (path := get_tos_root(search_path)).is_dir():
            yield path


def get_tos_dir(
    tos_root: str | os.PathLike[str] | Path, channel: str | Channel
) -> Path:
    """Get the ToS directory for the given channel."""
    return get_tos_root(tos_root) / hash_channel(channel)


def get_tos_path(
    tos_root: str | os.PathLike[str] | Path, channel: str | Channel, version: int
) -> Path:
    """Get the ToS file path for the given channel and version."""
    return get_tos_dir(tos_root, channel) / f"{version}.json"
