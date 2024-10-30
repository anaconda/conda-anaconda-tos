# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS cache functions."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from conda.models.channel import Channel

from .exceptions import CondaToSMissingError
from .local import get_local_metadata, read_metadata, touch_cache, write_metadata
from .path import get_all_paths, get_cache_path, get_tos_search_path
from .remote import get_remote_metadata

if TYPE_CHECKING:
    import os
    from pathlib import Path
    from typing import Iterator

    from .models import LocalToSMetadata, RemoteToSMetadata


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
    tos_root: str | os.PathLike[str] | Path, channel: str | Channel
) -> tuple[RemoteToSMetadata, Path] | tuple[None, None]:
    try:
        # fetch remote metadata
        metadata = get_remote_metadata(channel)
    except CondaToSMissingError:
        # CondaToSMissingError: no ToS for this channel
        touch_cache(channel)
        return None, None
    else:
        # cache metadata for future use
        path = write_metadata(tos_root, channel, metadata)
        return metadata, path


def get_metadata(
    tos_root: str | os.PathLike[str] | Path, channel: str | Channel, cache_timeout: int
) -> tuple[RemoteToSMetadata | LocalToSMetadata, Path] | tuple[None, None]:
    """Get the ToS metadata for the given channel."""
    if is_cache_stale(channel, cache_timeout):
        return _cache_remote_metadata(tos_root, channel)

    # return cached metadata
    return get_local_metadata(channel)


def get_all_metadatas(
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int,
) -> Iterator[tuple[Channel, RemoteToSMetadata | LocalToSMetadata, Path]]:
    """Yield all ToS metadatas."""
    grouped_metadata: dict[
        Channel, list[tuple[RemoteToSMetadata | LocalToSMetadata, Path]]
    ] = {}
    for tos_root in get_tos_search_path():
        for path in get_all_paths(tos_root):
            if metadata := read_metadata(path):
                channel = Channel(metadata.base_url)
                if is_cache_stale(channel, cache_timeout):
                    metadata, path = _cache_remote_metadata(tos_root, channel)
                grouped_metadata.setdefault(channel, []).append((metadata, path))

    for channel, metadata_tuples in grouped_metadata.items():
        yield (channel, *sorted(metadata_tuples, key=lambda x: x[0].tos_version)[-1])
