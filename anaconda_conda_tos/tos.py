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

from conda.gateways.disk.delete import rm_rf
from conda.base.context import context
from conda.common.url import join_url
from conda.models.channel import Channel
from conda.gateways.connection.session import get_session

if TYPE_CHECKING:
    from typing import Literal, Final, Iterable
    from requests import Response


# local
TOS_DIRECTORY: Final = "conda-meta/tos"

# remote endpoints
TOS_METADATA: Final = "tos.json"
TOS_TEXT: Final = "tos.txt"


def get_tos_dir(channel: Channel) -> Path:
    return Path(context.target_prefix, TOS_DIRECTORY, _hash_channel(channel))


def get_tos_path(channel: Channel, version: int) -> Path:
    return get_tos_dir(channel) / f"{version}.json"


def _hash_channel(channel: Channel) -> str:
    hasher = hashlib.new("sha256")
    hasher.update(channel.channel_location.encode("utf-8"))
    hasher.update(channel.channel_name.encode("utf-8"))
    return hasher.hexdigest()


def _get_tos(channel: Channel, endpoint: Literal["tos.json", "tos.txt"]) -> Response:
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


def get_tos_metadata(channel: Channel) -> dict:
    if not channel.base_url:
        raise TypeError("Channel must have a base URL to get ToS metadata.")

    return _get_tos(channel, TOS_METADATA).json()


def get_tos_text(channel: Channel) -> str:
    if not channel.base_url:
        raise TypeError("Channel must have a base URL to get ToS text.")

    return _get_tos(channel, TOS_TEXT).text


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


def view_tos(*channels: str | Channel) -> None:
    """Prints the ToS text for the given channels."""
    for channel in get_channels(*channels):
        print(f"viewing ToS for {channel}:")
        print(get_tos_text(channel))


def accept_tos(*channels: str | Channel) -> None:
    """Accepts the ToS for the given channels."""
    for channel in get_channels(*channels):
        print(f"accepting ToS for {channel}")
        tos_metadata = get_tos_metadata(channel)
        tos_path = get_tos_path(channel, tos_metadata["tos_version"])
        tos_path.parent.mkdir(parents=True, exist_ok=True)
        tos_path.write_text(
            json.dumps(
                {
                    **tos_metadata,
                    "tos_accepted": True,
                    "acceptance_timestamp": datetime.utcnow().timestamp(),
                    "url": channel.base_url,
                }
            )
        )


def reject_tos(*channels: str | Channel) -> None:
    """Removes the ToS directory for the given channels."""
    for channel in get_channels(*channels):
        print(f"declining ToS for {channel}")
        rm_rf(get_tos_dir(channel))


def list_tos() -> None:
    """Lists all channels and whether their ToS has been accepted."""
    pass
