# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
ToS management functions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.base.context import context
from conda.common.url import join_url
from conda.models.channel import Channel
from conda.gateways.connection.session import get_session
from requests import HTTPError

from .exceptions import CondaToSError

if TYPE_CHECKING:
    from typing import Literal, Final, Iterable
    from requests import Response


# remote endpoints
TOS_TEXT: Final = "tos.txt"


def get_tos_endpoint(
    channel: str | Channel,
    endpoint: Literal["tos.json", "tos.txt"],
) -> Response:
    channel = Channel(channel)
    if not channel.base_url:
        raise TypeError(
            "Channel must have a base URL. MultiChannel doesn't have endpoints."
        )

    session = get_session(channel.base_url)
    endpoint = join_url(channel.base_url, TOS_TEXT)

    saved_token_setting = context.add_anaconda_token
    try:
        # do not inject conda/binstar token into URL for two reasons:
        # 1. ToS shouldn't be a protected endpoint
        # 2. CondaHttpAuth.add_binstar_token adds subdir to the URL which ToS don't have
        context.add_anaconda_token = False
        response = session.get(
            endpoint,
            headers={"Content-Type": "text/plain"},
            proxies=session.proxies,
            auth=None,
            timeout=(
                context.remote_connect_timeout_secs,
                context.remote_read_timeout_secs,
            ),
        )
        response.raise_for_status()
    except HTTPError as exc:
        if exc.response.status_code == 404:
            raise CondaToSError(f"ToS endpoint ({endpoint}) not found")
        else:
            raise
    finally:
        context.add_anaconda_token = saved_token_setting
    return response


def get_channels(*channels: str | Channel) -> Iterable[Channel]:
    # expand every multichannel into its individual channels
    # and remove any duplicates
    seen: set[Channel] = set()
    for multichannel in map(Channel, channels):
        for channel in map(Channel, multichannel.urls()):
            channel = Channel(channel.base_url)
            if channel not in seen:
                yield channel
                seen.add(channel)


def get_tos_text(channel: str | Channel) -> str:
    return get_tos_endpoint(channel, TOS_TEXT).text


def view_tos(*channels: str | Channel) -> None:
    """Prints the ToS text for the given channels."""
    for channel in get_channels(*channels):
        print(f"viewing ToS for {channel}:")
        print(get_tos_text(channel))
