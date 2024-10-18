# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS management functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.models.channel import Channel

from .exceptions import CondaToSMissingError
from .metadata import (
    get_all_tos_metadatas,
    get_channel_tos_metadata,
    write_metadata,
)
from .remote import get_tos_metadata, get_tos_text

if TYPE_CHECKING:
    from typing import Iterable, Iterator

    from .metadata import ToSMetadata


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


def view_tos(*channels: str | Channel) -> None:
    """Print the ToS full text for the given channels."""
    for channel in get_channels(*channels):
        print(f"viewing ToS for {channel}:")
        try:
            print(get_tos_text(channel))
        except CondaToSMissingError:
            print("ToS not found")


def accept_tos(*channels: str | Channel) -> None:
    """Accept the ToS for the given channels."""
    for channel in get_channels(*channels):
        try:
            metadata = get_tos_metadata(channel)
        except CondaToSMissingError:
            print(f"ToS not found for {channel}")
        else:
            print(f"accepting ToS for {channel}")
            write_metadata(channel, metadata, tos_accepted=True)


def reject_tos(*channels: str | Channel) -> None:
    """Reject the ToS for the given channels."""
    for channel in get_channels(*channels):
        try:
            metadata = get_tos_metadata(channel)
        except CondaToSMissingError:
            print(f"ToS not found for {channel}")
        else:
            print(f"rejecting ToS for {channel}")
            write_metadata(channel, metadata, tos_accepted=False)


def get_tos(*channels: str | Channel) -> Iterator[tuple[Channel, ToSMetadata | None]]:
    """List all channels and whether their ToS has been accepted."""
    # list all active channels
    seen: set[Channel] = set()
    for channel in get_channels(*channels):
        yield channel, get_channel_tos_metadata(channel)
        seen.add(channel)

    # list all other ToS that have been accepted
    for channel, metadata in get_all_tos_metadatas():
        if channel not in seen:
            yield channel, metadata
            seen.add(channel)
