# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

from .exceptions import CondaToSMissingError
from .local import get_local_metadata, get_local_metadatas
from .models import MetadataPathPair
from .remote import get_remote_metadata

if TYPE_CHECKING:
    import os
    from pathlib import Path
    from typing import Iterator

    from conda.models.channel import Channel


def get_metadata(
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


def get_all_metadatas(
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
