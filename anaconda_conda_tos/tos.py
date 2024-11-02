# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS management functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .api import get_channels, get_single_metadata
from .exceptions import CondaToSMissingError
from .local import write_metadata

if TYPE_CHECKING:
    import os
    from pathlib import Path

    from conda.models.channel import Channel


def view_tos(
    *channels: str | Channel,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int | float | None,
) -> None:
    """Print the ToS full text for the given channels."""
    for channel in get_channels(*channels):
        print(f"viewing ToS for {channel}:")
        try:
            print(
                get_single_metadata(
                    channel, tos_root, cache_timeout=cache_timeout
                ).metadata.text
            )
        except CondaToSMissingError:
            print("ToS not found")


def accept_tos(
    *channels: str | Channel,
    tos_root: str | os.PathLike | Path,
    cache_timeout: int | float | None,
) -> None:
    """Accept the ToS for the given channels."""
    for channel in get_channels(*channels):
        try:
            metadata = get_single_metadata(
                channel, tos_root, cache_timeout=cache_timeout
            ).metadata
        except CondaToSMissingError:
            print(f"ToS not found for {channel}")
        else:
            print(f"accepting ToS for {channel}")
            write_metadata(tos_root, channel, metadata, tos_accepted=True)


def reject_tos(
    *channels: str | Channel,
    tos_root: str | os.PathLike | Path,
    cache_timeout: int | float | None,
) -> None:
    """Reject the ToS for the given channels."""
    for channel in get_channels(*channels):
        try:
            metadata = get_single_metadata(
                channel, tos_root, cache_timeout=cache_timeout
            ).metadata
        except CondaToSMissingError:
            print(f"ToS not found for {channel}")
        else:
            print(f"rejecting ToS for {channel}")
            write_metadata(tos_root, channel, metadata, tos_accepted=False)
