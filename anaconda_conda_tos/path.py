# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS path functions."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.models.channel import Channel

if TYPE_CHECKING:
    from typing import Final

TOS_DIRECTORY: Final = "conda-meta/tos"


def hash_channel(channel: str | Channel) -> str:
    """Hash the channel to remove problematic characters (e.g. /)."""
    channel = Channel(channel)
    if not channel.base_url:
        raise ValueError("Channel must have a base URL. MultiChannel cannot be hashed.")

    hasher = hashlib.new("sha256")
    hasher.update(channel.channel_location.encode("utf-8"))
    hasher.update(channel.channel_name.encode("utf-8"))
    return hasher.hexdigest()


def get_tos_dir(channel: str | Channel) -> Path:
    """Get the ToS directory for the given channel."""
    return Path(context.target_prefix, TOS_DIRECTORY, hash_channel(channel))


def get_tos_path(channel: str | Channel, version: int) -> Path:
    """Get the ToS file path for the given channel and version."""
    return get_tos_dir(channel) / f"{version}.json"
