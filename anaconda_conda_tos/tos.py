# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
ToS management functions.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import TYPE_CHECKING
from pathlib import Path
import json

from conda.base.context import context
from conda.common.url import join_url
from conda.models.channel import Channel
from conda.gateways.connection.session import get_session

if TYPE_CHECKING:
    from typing import Literal, Final, Iterable, TypedDict, Iterator
    from requests import Response

    class ToSMetaData(TypedDict):
        tos_accepted: bool | None
        tos_version: int
        acceptance_timestamp: float
        base_url: str | None


# remote endpoints
TOS_TEXT: Final = "tos.txt"


def get_tos_endpoint(
    channel: str | Channel, endpoint: Literal["tos.json", "tos.txt"]
) -> Response:
    channel = Channel(channel)
    if not channel.base_url:
        raise TypeError(
            "Channel must have a base URL. MultiChannel doesn't have endpoints."
        )

    session = get_session(channel.base_url)

    response = session.get(
        join_url(channel.base_url, TOS_TEXT),
        headers={"Content-Type": "text/plain"},
        proxies=session.proxies,
        auth=None,
        timeout=(context.remote_connect_timeout_secs, context.remote_read_timeout_secs),
    )
    response.raise_for_status()
    return response


def get_channels(*channels: str | Channel) -> Iterable[Channel]:
    # expand every multichannel into its individual channels
    # and remove any duplicates
    seen: set[Channel] = set()
    for multichannel in map(Channel, channels):
        for channel in map(Channel, multichannel.urls()):
            if channel in seen:
                continue
            seen.add(channel)
            yield channel


def get_tos_text(channel: str | Channel) -> str:
    return get_tos_endpoint(channel, TOS_TEXT).text


def view_tos(*channels: str | Channel) -> None:
    """Prints the ToS text for the given channels."""
    for channel in get_channels(*channels):
        print(f"viewing ToS for {channel}:")
        print(get_tos_text(channel))
