# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS metadata functions."""

from __future__ import annotations

from datetime import datetime  # noqa: TCH003 # pydantic needs datetime at runtime

from conda.models.channel import Channel

from .path import get_tos_path
from .remote import RemoteToSMetadata


class ToSMetadata(RemoteToSMetadata):
    """Conda ToS metadata schema with acceptance fields."""

    tos_accepted: bool
    acceptance_timestamp: datetime
    base_url: str


def write_metadata(
    channel: Channel,
    metadata: ToSMetadata | RemoteToSMetadata,
    # kwargs extends/overrides metadata fields
    **kwargs: int | bool | datetime | float | str,
) -> None:
    """Write the ToS metadata to file."""
    # argument validation/coercion
    channel = Channel(channel)
    if not channel.base_url:
        raise ValueError("`channel` must have a base URL.")
    if not isinstance(metadata, (ToSMetadata, RemoteToSMetadata)):
        raise TypeError("`metadata` must be either a ToSMetadata or RemoteToSMetadata.")
    metadata = ToSMetadata(
        **{**metadata.model_dump(), **kwargs, "base_url": channel.base_url}
    )

    # write metadata to file
    path = get_tos_path(channel, metadata.tos_version)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(metadata.model_dump_json())
