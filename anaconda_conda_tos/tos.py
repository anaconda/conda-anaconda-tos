# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS management functions."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.models.channel import Channel

from .exceptions import CondaToSMissingError
from .metadata import read_metadata, write_metadata
from .path import TOS_DIRECTORY, get_tos_dir
from .remote import get_tos_metadata, get_tos_text

if TYPE_CHECKING:
    from typing import Final, Iterable, Iterator

    from .metadata import ToSMetaData


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
        print(f"accepting ToS for {channel}")
        metadata = get_tos_metadata(channel)
        write_metadata(
            channel,
            tos_accepted=True,
            acceptance_timestamp=datetime.now(tz=timezone.utc),
            **metadata,
        )


def reject_tos(*channels: str | Channel) -> None:
    """Reject the ToS for the given channels."""
    for channel in get_channels(*channels):
        print(f"declining ToS for {channel}")
        metadata = get_tos_metadata(channel)
        write_metadata(channel, tos_accepted=False, **metadata)


UNDEFINED_TOS_METADATA: Final[ToSMetaData] = {
    "tos_accepted": None,
    "tos_version": 0,
    "acceptance_timestamp": 0,
    "base_url": None,
}


def get_current_tos_metadata(channel: Channel) -> ToSMetaData:
    """Get the current ToS metadata for the given channel."""
    try:
        # return the newest metadata
        _, metadata = next(get_tos_metadatas(channel))
        return metadata
    except StopIteration:
        # StopIteration: no metadata found
        return UNDEFINED_TOS_METADATA  # fallback metadata if none found


def get_tos_metadatas(
    channel: Channel | None = None,
) -> Iterator[tuple[Channel, ToSMetaData]]:
    """Yield all ToS metadata for the given channel."""
    if channel is None:
        paths = Path(context.target_prefix, TOS_DIRECTORY).glob("*/*.json")
    else:
        paths = get_tos_dir(channel).glob("*.json")

    # group metadata by channel
    grouped_metadatas: dict[Channel, list[ToSMetaData]] = {}
    for path in paths:
        if metadata := read_metadata(path):
            key = channel or Channel(metadata["base_url"])
            grouped_metadatas.setdefault(key, []).append(metadata)

    # return the newest metadata for each channel
    for channel, metadatas in grouped_metadatas.items():
        yield channel, sorted(metadatas, key=lambda x: x["tos_version"])[-1]


def get_tos(*channels: str | Channel) -> Iterator[tuple[Channel, ToSMetaData]]:
    """List all channels and whether their ToS has been accepted."""
    # list all active channels
    seen: set[Channel] = set()
    for channel in get_channels(*channels):
        yield channel, get_current_tos_metadata(channel)
        seen.add(channel)

    # list all other ToS that have been accepted
    for channel, metadata in get_tos_metadatas():
        if channel not in seen:
            yield channel, metadata
            seen.add(channel)
