# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS cache functions."""

from __future__ import annotations

from contextlib import suppress
from datetime import datetime
from typing import TYPE_CHECKING

from conda.models.channel import Channel

from .exceptions import CondaToSMissingError
from .local import get_local_metadata, read_metadata, touch_cache, write_metadata
from .models import MetadataPathPair
from .path import get_all_paths, get_cache_path, get_tos_search_path
from .remote import get_remote_metadata

if TYPE_CHECKING:
    import os
    from pathlib import Path
    from typing import Iterator


def is_cache_stale(channel: str | Channel, cache_timeout: int) -> bool:
    """Check if the (per user) cache is stale."""
    try:
        cache = get_cache_path(channel).stat().st_mtime
    except FileNotFoundError:
        # FileNotFoundError: cache path doesn't exist
        return True
    else:
        now = datetime.now().timestamp()  # noqa: DTZ005
        return (now - cache) >= cache_timeout


def _cache_remote_metadata(
    tos_root: str | os.PathLike[str] | Path,
    channel: str | Channel,
) -> MetadataPathPair:
    try:
        # fetch remote metadata
        metadata = get_remote_metadata(channel)
    except CondaToSMissingError:
        # CondaToSMissingError: no ToS for this channel
        touch_cache(channel)
        raise
    else:
        # cache metadata for future use
        return write_metadata(tos_root, channel, metadata)


def get_metadata(
    tos_root: str | os.PathLike[str] | Path,
    channel: str | Channel,
    cache_timeout: int,
) -> MetadataPathPair:
    """Get the ToS metadata for the given channel."""
    if not is_cache_stale(channel, cache_timeout):
        # return cached metadata
        return get_local_metadata(channel)

    try:
        remote_metadata = get_remote_metadata(channel)
    except CondaToSMissingError:
        # CondaToSMissingError: no ToS for this channel
        touch_cache(channel)
        return get_local_metadata(channel)

    # attempt to fetch local ToS metadata, if it exists we return the
    try:
        local_tuple = get_local_metadata(channel)
    except CondaToSMissingError:
        pass
    else:
        # successfully fetched local ToS metadata
        # reuse local metadata if it's the same or newer than the remote metadata
        if local_tuple.metadata.tos_version >= remote_metadata.tos_version:
            touch_cache(channel)
            return local_tuple

    # cache is stale, remote ToS metadata exists, and local ToS metadata is missing or
    # local ToS metadata is outdated (i.e., remote has a newer version)
    return write_metadata(tos_root, channel, remote_metadata)


def get_all_metadatas(
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int,
) -> Iterator[tuple[Channel, MetadataPathPair]]:
    """Yield all ToS metadatas."""
    # group all ToS metadata files by their channel
    channel_metadata_pairs: dict[Channel, list[MetadataPathPair]] = {}
    for tos_root in get_tos_search_path():
        for path in get_all_paths(tos_root):
            if metadata := read_metadata(path):
                channel = Channel(metadata.base_url)
                metadata_pair = MetadataPathPair(metadata=metadata, path=path)
                channel_metadata_pairs.setdefault(channel, []).append(metadata_pair)

    # yield the latest ToS metadata for each channel
    for channel, metadata_pairs in channel_metadata_pairs.items():
        # return cached metadata if not stale
        if not is_cache_stale(channel, cache_timeout):
            yield (
                channel,
                sorted(
                    metadata_pairs,
                    key=lambda metadata_pair: metadata_pair.metadata.tos_version,
                )[-1],
            )
        # return remote metadata if it exists
        with suppress(CondaToSMissingError):
            yield channel, _cache_remote_metadata(tos_root, channel)
        # otherwise skip
