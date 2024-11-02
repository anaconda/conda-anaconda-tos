# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS API functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.models.channel import Channel

from .exceptions import CondaToSMissingError
from .local import get_local_metadata, get_local_metadatas
from .models import MetadataPathPair
from .remote import get_remote_metadata

if TYPE_CHECKING:
    import os
    from pathlib import Path
    from typing import Iterable, Iterator


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


def get_single_metadata(
    channel: str | Channel,
    tos_root: str | os.PathLike[str] | Path,
    *,
    cache_timeout: int | float | None,
) -> MetadataPathPair:
    """Get the ToS metadata for the given channel."""
    # fetch remote metadata
    remote_metadata = get_remote_metadata(channel, cache_timeout=cache_timeout)

    # fetch local metadata
    try:
        local_pair = get_local_metadata(channel, extend_search_path=[tos_root])
    except CondaToSMissingError:
        # CondaToSMissingError: no local ToS metadata
        pass
    else:
        # return local metadata if it's the same version as the remote
        if local_pair.metadata.tos_version >= remote_metadata.tos_version:
            return local_pair

    # cache is stale, remote ToS metadata exists, and local ToS metadata is missing or
    # local ToS metadata is outdated (i.e., remote has a newer version)
    return MetadataPathPair(metadata=remote_metadata)


def get_stored_metadatas(
    tos_root: str | os.PathLike[str] | Path,
    *,
    cache_timeout: int | float | None,
) -> Iterator[tuple[Channel, MetadataPathPair]]:
    """Yield all ToS metadatas."""
    for channel, local_pair in get_local_metadatas(extend_search_path=[tos_root]):
        try:
            remote_metadata = get_remote_metadata(channel, cache_timeout=cache_timeout)
        except CondaToSMissingError:
            # CondaToSMissingError: no remote ToS metadata
            continue

        # yield local metadata if it's the same version as the remote
        if local_pair.metadata.tos_version >= remote_metadata.tos_version:
            yield channel, local_pair
        else:
            yield channel, MetadataPathPair(metadata=remote_metadata)


def get_all_metadatas(
    *channels: str | Channel,
    tos_root: str | os.PathLike | Path,
    cache_timeout: int | float | None,
) -> Iterator[tuple[Channel, MetadataPathPair | None]]:
    """List all channels and whether their ToS has been accepted."""
    # list all active channels
    seen: set[Channel] = set()
    for channel in get_channels(*channels):
        try:
            yield (
                channel,
                get_single_metadata(channel, tos_root, cache_timeout=cache_timeout),
            )
        except CondaToSMissingError:
            yield channel, None
        seen.add(channel)

    # list all other ToS that have been accepted/rejected
    for channel, metadata_pair in get_stored_metadatas(
        tos_root, cache_timeout=cache_timeout
    ):
        if channel not in seen:
            yield channel, metadata_pair
            seen.add(channel)
