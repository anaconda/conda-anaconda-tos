# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS metadata management functions."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.models.channel import Channel

from .path import TOS_DIRECTORY, get_tos_dir, get_tos_path

if TYPE_CHECKING:
    from typing import Final, Iterator, TypedDict

    class ToSMetaData(TypedDict):
        """ToS metadata."""

        tos_accepted: bool | None
        tos_version: int
        acceptance_timestamp: float
        base_url: str | None


UNDEFINED_TOS_METADATA: Final[ToSMetaData] = {
    "tos_accepted": None,
    "tos_version": 0,
    "acceptance_timestamp": 0,
    "base_url": None,
}


def write_metadata(
    channel: Channel,
    *,
    tos_version: int,
    tos_accepted: bool,
    acceptance_timestamp: datetime | float = 0,
    **metadata,  # noqa: ANN003
) -> None:
    """Write the ToS metadata to file."""
    # argument validation/coercion
    channel = Channel(channel)
    if not channel.base_url:
        raise TypeError("`channel` must have a base URL.")
    if not isinstance(tos_version, int):
        raise TypeError("`tos_version` must be an `int`.")
    tos_accepted = bool(tos_accepted)
    if isinstance(acceptance_timestamp, datetime):
        acceptance_timestamp = acceptance_timestamp.timestamp()
    elif not isinstance(acceptance_timestamp, float):
        raise TypeError("`timestamp` must be a `datetime` or a `float`.")

    # write metadata to file
    path = get_tos_path(channel, tos_version)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                **metadata,
                "tos_version": tos_version,
                "tos_accepted": tos_accepted,
                "acceptance_timestamp": acceptance_timestamp,
                "base_url": channel.base_url,
            },
            sort_keys=True,
        )
    )


def read_metadata(path: Path) -> ToSMetaData | None:
    """Load the ToS metadata from file."""
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        # OSError: unable to access file, ignoring
        # JSONDecodeError: corrupt file, ignoring
        return None


def get_channel_tos_metadata(channel: Channel) -> ToSMetaData:
    """Get the current ToS metadata for the given channel."""
    try:
        # return the newest metadata
        _, metadata = next(get_all_tos_metadatas(channel))
        return metadata
    except StopIteration:
        # StopIteration: no metadata found
        return UNDEFINED_TOS_METADATA  # fallback metadata if none found


def get_all_tos_metadatas(
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
