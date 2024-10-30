# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS management functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.models.channel import Channel

from .cache import get_all_metadatas, get_metadata
from .exceptions import CondaToSMissingError
from .local import write_metadata

if TYPE_CHECKING:
    import os
    from pathlib import Path
    from typing import Iterable, Iterator

    from .models import LocalToSMetadata


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


def view_tos(
    tos_root: str | os.PathLike[str] | Path,
    *channels: str | Channel,
    cache_timeout: int,
) -> None:
    """Print the ToS full text for the given channels."""
    for channel in get_channels(*channels):
        print(f"viewing ToS for {channel}:")
        try:
            metadata, _ = get_metadata(tos_root, channel, cache_timeout)
            print(metadata.text)
        except CondaToSMissingError:
            print("ToS not found")


def accept_tos(
    tos_root: str | os.PathLike | Path, *channels: str | Channel, cache_timeout: int
) -> None:
    """Accept the ToS for the given channels."""
    for channel in get_channels(*channels):
        try:
            metadata, _ = get_metadata(tos_root, channel, cache_timeout)
        except CondaToSMissingError:
            print(f"ToS not found for {channel}")
        else:
            print(f"accepting ToS for {channel}")
            write_metadata(tos_root, channel, metadata, tos_accepted=True)


def reject_tos(
    tos_root: str | os.PathLike | Path, *channels: str | Channel, cache_timeout: int
) -> None:
    """Reject the ToS for the given channels."""
    for channel in get_channels(*channels):
        try:
            metadata, _ = get_metadata(tos_root, channel, cache_timeout)
        except CondaToSMissingError:
            print(f"ToS not found for {channel}")
        else:
            print(f"rejecting ToS for {channel}")
            write_metadata(tos_root, channel, metadata, tos_accepted=False)


def get_tos(
    tos_root: str | os.PathLike[str] | Path,
    *channels: str | Channel,
    cache_timeout: int,
) -> Iterator[tuple[Channel, LocalToSMetadata, Path] | tuple[Channel, None, None]]:
    """List all channels and whether their ToS has been accepted."""
    # list all active channels
    seen: set[Channel] = set()
    for channel in get_channels(*channels):
        yield channel, *get_metadata(tos_root, channel, cache_timeout)
        seen.add(channel)

    # list all other ToS that have been accepted/rejected
    for channel, metadata, path in get_all_metadatas(tos_root, cache_timeout):
        if channel not in seen:
            yield channel, metadata, path
            seen.add(channel)
