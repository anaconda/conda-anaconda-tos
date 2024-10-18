# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS remote functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.base.context import context
from conda.common.url import join_url
from conda.gateways.connection.session import get_session
from conda.models.channel import Channel
from requests import HTTPError

from .exceptions import CondaToSMissingError

if TYPE_CHECKING:
    from typing import Final, Literal

    from requests import Response

TOS_TEXT_ENDPOINT: Final = "tos.txt"
TOS_METADATA_ENDPOINT: Final = "tos.json"


def get_tos_endpoint(
    channel: str | Channel,
    endpoint: Literal["tos.txt", "tos.json"],
) -> Response:
    """Get the ToS endpoint for the given channel."""
    channel = Channel(channel)
    if not channel.base_url:
        raise ValueError(
            "Channel must have a base URL. MultiChannel doesn't have endpoints."
        )
    if endpoint not in (TOS_TEXT_ENDPOINT, TOS_METADATA_ENDPOINT):
        raise ValueError(f"Invalid ToS endpoint: {endpoint}")

    session = get_session(channel.base_url)
    url = join_url(channel.base_url, endpoint)

    saved_token_setting = context.add_anaconda_token
    try:
        # do not inject conda/binstar token into URL for two reasons:
        # 1. ToS shouldn't be a protected endpoint
        # 2. CondaHttpAuth.add_binstar_token adds subdir to the URL which ToS don't have
        context.add_anaconda_token = False
        response = session.get(
            url,
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
            raise CondaToSMissingError(channel) from exc
        else:
            raise
    finally:
        context.add_anaconda_token = saved_token_setting
    return response


def get_tos_text(channel: str | Channel) -> str:
    """Get the ToS full text for the given channel."""
    return get_tos_endpoint(channel, TOS_TEXT_ENDPOINT).text.rstrip()


def get_tos_metadata(channel: str | Channel) -> dict:
    """Get the ToS metadata for the given channel."""
    return get_tos_endpoint(channel, TOS_METADATA_ENDPOINT).json()
