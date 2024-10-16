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


# local
TOS_DIRECTORY: Final = "conda-meta/tos"

# remote endpoints
TOS_METADATA: Final = "tos.json"
TOS_TEXT: Final = "tos.txt"


def get_tos_dir(channel: str | Channel) -> Path:
    return Path(context.target_prefix, TOS_DIRECTORY, hash_channel(channel))


def get_tos_path(channel: str | Channel, version: int) -> Path:
    return get_tos_dir(channel) / f"{version}.json"


def hash_channel(channel: str | Channel) -> str:
    channel = Channel(channel)
    if not channel.base_url:
        raise TypeError("Channel must have a base URL. MultiChannel cannot be hashed.")

    hasher = hashlib.new("sha256")
    hasher.update(channel.channel_location.encode("utf-8"))
    hasher.update(channel.channel_name.encode("utf-8"))
    return hasher.hexdigest()


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


def get_tos_metadata(channel: str | Channel) -> dict:
    return get_tos_endpoint(channel, TOS_METADATA).json()


def get_tos_text(channel: str | Channel) -> str:
    return get_tos_endpoint(channel, TOS_TEXT).text


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


def write_metadata(
    channel: Channel,
    *,
    tos_version: int,
    tos_accepted: bool,
    acceptance_timestamp: datetime | float = 0,
    **metadata,
) -> None:
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


def accept_tos(*channels: str | Channel) -> None:
    """Accepts the ToS for the given channels."""
    for channel in get_channels(*channels):
        print(f"accepting ToS for {channel}")
        metadata = get_tos_metadata(channel)
        write_metadata(
            channel,
            tos_accepted=True,
            acceptance_timestamp=datetime.utcnow(),
            **metadata,
        )


def reject_tos(*channels: str | Channel) -> None:
    """Removes the ToS directory for the given channels."""
    for channel in get_channels(*channels):
        print(f"declining ToS for {channel}")
        metadata = get_tos_metadata(channel)
        write_metadata(channel, tos_accepted=False, **metadata)


UNDEFINED_TOS_METADATA: Final[ToSMetaData] = {
    "tos_accepted": None,
    "tos_version": 0,
    "acceptance_timestamp": 0,
    "base_url": None,
}


def load_metadata(path: Path) -> ToSMetaData | None:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        # OSError: unable to access file, ignoring
        # JSONDecodeError: corrupt file, ignoring
        return None


def get_current_tos_metadata(channel: Channel) -> ToSMetaData:
    try:
        # return the newest metadata
        _, metadata = next(get_tos_metadatas(channel))
        return metadata
    except StopIteration:
        # StopIteration: no metadata found
        return UNDEFINED_TOS_METADATA  # fallback metadata if none found


def get_tos_metadatas(
    channel: Channel | None = None,
) -> Iterator[tuple[Channel, ToSMetaData]]:
    if channel is None:
        paths = Path(context.target_prefix, TOS_DIRECTORY).glob("*/*.json")
    else:
        paths = get_tos_dir(channel).glob("*.json")

    # group metadata by channel
    grouped_metadatas: dict[Channel, list[ToSMetaData]] = {}
    for path in paths:
        if metadata := load_metadata(path):
            key = channel or Channel(metadata["base_url"])
            grouped_metadatas.setdefault(key, []).append(metadata)

    # return the newest metadata for each channel
    for channel, metadatas in grouped_metadatas.items():
        yield channel, sorted(metadatas, key=lambda x: x["tos_version"])[-1]


def get_tos(*channels: str | Channel) -> Iterator[tuple[Channel, ToSMetaData]]:
    """Lists all channels and whether their ToS has been accepted."""
    # list all active channels
    seen: set[Channel] = set()
    for channel in get_channels(*context.channels):
        yield channel, get_current_tos_metadata(channel)
        seen.add(channel)

    # list all other ToS that have been accepted
    for channel, metadata in get_tos_metadatas():
        if channel not in seen:
            yield channel, metadata
            seen.add(channel)
