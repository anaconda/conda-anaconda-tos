# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS metadata functions."""

from __future__ import annotations

import json
from datetime import datetime

from conda.models.channel import Channel

from .path import get_tos_path


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
        raise ValueError("`channel` must have a base URL.")
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
