# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS management functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.models.channel import Channel

from .exceptions import CondaToSMissingError
from .local import (
    get_all_local_metadatas,
    get_local_metadata,
    write_metadata,
)
from .remote import get_metadata

if TYPE_CHECKING:
    import os
    from pathlib import Path
    from typing import Iterable, Iterator

    from .models import MetadataPathPair


def get_channels(*channels: str | Channel) -> Iterable[Channel]:
    """Yield all unique channels from the given channels."""
    # expand every multichannel into its individual channels
    # and remove any duplicates
    seen: set[Channel] = set()
    for multichannel in map(Channel, channels):
        for channel in map(Channel, multichannel.urls()):
            channel = Channel(channel.base_url)
            if channel not in seen:
                yield channel
                seen.add(channel)


def accept_tos(
    tos_root: str | os.PathLike | Path,
    channel: str | Channel,
) -> MetadataPathPair:
    """Accept the ToS for the given channel."""
    metadata = get_metadata(channel)
    return write_metadata(tos_root, channel, metadata, tos_accepted=True)


def reject_tos(
    tos_root: str | os.PathLike | Path,
    channel: str | Channel,
) -> MetadataPathPair:
    """Reject the ToS for the given channel."""
    metadata = get_metadata(channel)
    return write_metadata(tos_root, channel, metadata, tos_accepted=False)


def get_tos(
    *channels: str | Channel,
) -> Iterator[tuple[Channel, MetadataPathPair | None]]:
    """List all channels and whether their ToS has been accepted."""
    # list all active channels
    seen: set[Channel] = set()
    for channel in get_channels(*channels):
        try:
            yield channel, get_local_metadata(channel)
        except CondaToSMissingError:
            yield channel, None
        seen.add(channel)

    # list all other ToS that have been accepted/rejected
    for channel, metadata_pair in get_all_local_metadatas():
        if channel not in seen:
            yield channel, metadata_pair
            seen.add(channel)
