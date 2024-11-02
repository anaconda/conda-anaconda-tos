# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS management functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.models.channel import Channel

from .api import get_all_metadatas, get_metadata
from .exceptions import CondaToSMissingError
from .local import write_metadata

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


def view_tos(
    *channels: str | Channel,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int | float | None,
) -> None:
    """Print the ToS full text for the given channels."""
    for channel in get_channels(*channels):
        print(f"viewing ToS for {channel}:")
        try:
            print(
                get_metadata(
                    channel, tos_root, cache_timeout=cache_timeout
                ).metadata.text
            )
        except CondaToSMissingError:
            print("ToS not found")


def accept_tos(
    *channels: str | Channel,
    tos_root: str | os.PathLike | Path,
    cache_timeout: int | float | None,
) -> None:
    """Accept the ToS for the given channels."""
    for channel in get_channels(*channels):
        try:
            metadata = get_metadata(
                channel, tos_root, cache_timeout=cache_timeout
            ).metadata
        except CondaToSMissingError:
            print(f"ToS not found for {channel}")
        else:
            print(f"accepting ToS for {channel}")
            write_metadata(tos_root, channel, metadata, tos_accepted=True)


def reject_tos(
    *channels: str | Channel,
    tos_root: str | os.PathLike | Path,
    cache_timeout: int | float | None,
) -> None:
    """Reject the ToS for the given channels."""
    for channel in get_channels(*channels):
        try:
            metadata = get_metadata(
                channel, tos_root, cache_timeout=cache_timeout
            ).metadata
        except CondaToSMissingError:
            print(f"ToS not found for {channel}")
        else:
            print(f"rejecting ToS for {channel}")
            write_metadata(tos_root, channel, metadata, tos_accepted=False)


def get_tos(
    *channels: str | Channel,
    tos_root: str | os.PathLike | Path,
    cache_timeout: int | float | None,
) -> Iterator[tuple[Channel, MetadataPathPair | None]]:
    """List all channels and whether their ToS has been accepted."""
    # list all active channels
    seen: set[Channel] = set()
    for channel in get_channels(*channels):
        try:
            yield channel, get_metadata(channel, tos_root, cache_timeout=cache_timeout)
        except CondaToSMissingError:
            yield channel, None
        seen.add(channel)

    # list all other ToS that have been accepted/rejected
    for channel, metadata_pair in get_all_metadatas(
        tos_root, cache_timeout=cache_timeout
    ):
        if channel not in seen:
            yield channel, metadata_pair
            seen.add(channel)
