# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS metadata functions."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.models.channel import Channel
from pydantic import ValidationError

from .path import TOS_DIRECTORY, get_tos_dir, get_tos_path
from .remote import RemoteToSMetadata

if TYPE_CHECKING:
    from typing import Any, Iterator


class ToSMetadata(RemoteToSMetadata):
    """Conda ToS metadata schema with acceptance fields."""

    tos_accepted: bool
    acceptance_timestamp: datetime
    base_url: str


def write_metadata(
    channel: Channel,
    metadata: ToSMetadata | RemoteToSMetadata,
    # kwargs extends/overrides metadata fields
    **kwargs: Any,  # noqa: ANN401
) -> None:
    """Write the ToS metadata to file."""
    # argument validation/coercion
    channel = Channel(channel)
    if not channel.base_url:
        raise ValueError("`channel` must have a base URL.")
    if not isinstance(metadata, (ToSMetadata, RemoteToSMetadata)):
        raise TypeError("`metadata` must be either a ToSMetadata or RemoteToSMetadata.")

    # create/update ToSMetadata object
    metadata = ToSMetadata(
        **{
            **metadata.model_dump(),
            **kwargs,
            # override the following fields with the current time and channel base URL
            "acceptance_timestamp": datetime.now(tz=timezone.utc),
            "base_url": channel.base_url,
        }
    )

    # write metadata to file
    path = get_tos_path(channel, metadata.tos_version)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(metadata.model_dump_json())


def read_metadata(path: Path) -> ToSMetadata | None:
    """Load the ToS metadata from file."""
    try:
        return ToSMetadata.model_validate_json(path.read_text())
    except (OSError, ValidationError):
        # OSError: unable to access file, ignoring
        # ValidationError: corrupt file, ignoring
        return None


def get_channel_tos_metadata(channel: Channel) -> ToSMetadata | None:
    """Get the current ToS metadata for the given channel."""
    try:
        # return the newest metadata
        _, metadata = next(get_all_tos_metadatas(channel))
        return metadata
    except StopIteration:
        # StopIteration: no metadata found
        return None


def get_all_tos_metadatas(
    channel: Channel | None = None,
) -> Iterator[tuple[Channel, ToSMetadata]]:
    """Yield all ToS metadata for the given channel."""
    if channel is None:
        paths = Path(context.target_prefix, TOS_DIRECTORY).glob("*/*.json")
    else:
        paths = get_tos_dir(channel).glob("*.json")

    # group metadata by channel
    grouped_metadatas: dict[Channel, list[ToSMetadata]] = {}
    for path in paths:
        if metadata := read_metadata(path):
            key = channel or Channel(metadata.base_url)
            grouped_metadatas.setdefault(key, []).append(metadata)

    # return the newest metadata for each channel
    for channel, metadatas in grouped_metadatas.items():
        yield channel, sorted(metadatas, key=lambda x: x.tos_version)[-1]
