# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS metadata functions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from conda.models.channel import Channel
from pydantic import ValidationError

from .models import LocalToSMetadata, RemoteToSMetadata
from .path import (
    get_all_channel_paths,
    get_channel_paths,
    get_tos_path,
)

if TYPE_CHECKING:
    import os
    from pathlib import Path
    from typing import Any, Iterator


def write_metadata(
    tos_root: str | os.PathLike[str] | Path,
    channel: Channel,
    metadata: LocalToSMetadata | RemoteToSMetadata,
    # kwargs extends/overrides metadata fields
    **kwargs: Any,  # noqa: ANN401
) -> None:
    """Write the ToS metadata to file."""
    # argument validation/coercion
    channel = Channel(channel)
    if not channel.base_url:
        raise ValueError("`channel` must have a base URL.")
    if not isinstance(metadata, (LocalToSMetadata, RemoteToSMetadata)):
        raise TypeError("`metadata` must be either a ToSMetadata or RemoteToSMetadata.")

    # create/update ToSMetadata object
    metadata = LocalToSMetadata(
        **{
            **metadata.model_dump(),
            **kwargs,
            # override the following fields with the current time and channel base URL
            "acceptance_timestamp": datetime.now(tz=timezone.utc),
            "base_url": channel.base_url,
        }
    )

    # write metadata to file
    path = get_tos_path(tos_root, channel, metadata.tos_version)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(metadata.model_dump_json())


def read_metadata(path: Path) -> LocalToSMetadata | None:
    """Load the ToS metadata from file."""
    try:
        return LocalToSMetadata.model_validate_json(path.read_text())
    except (OSError, ValidationError):
        # OSError: unable to access file, ignoring
        # ValidationError: corrupt file, ignoring
        return None


def get_channel_tos_metadata(
    channel: Channel,
) -> tuple[LocalToSMetadata, Path] | tuple[None, None]:
    """Get the current ToS metadata for the given channel."""
    try:
        # return the newest metadata
        _, metadata, path = next(get_all_tos_metadatas(channel))
        return metadata, path
    except StopIteration:
        # StopIteration: no metadata found
        return None, None


def get_all_tos_metadatas(
    channel: Channel | None = None,
) -> Iterator[tuple[Channel, LocalToSMetadata, Path]]:
    """Yield all ToS metadata for the given channel."""
    # group metadata by channel
    grouped_metadatas: dict[Channel, list[tuple[LocalToSMetadata, Path]]] = {}
    for path in get_channel_paths(channel) if channel else get_all_channel_paths():
        if metadata := read_metadata(path):
            key = channel or Channel(metadata.base_url)
            grouped_metadatas.setdefault(key, []).append((metadata, path))

    # return the newest metadata for each channel
    for channel, metadata_tuples in grouped_metadatas.items():
        yield (channel, *sorted(metadata_tuples, key=lambda x: x[0].tos_version)[-1])
