# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Custom exceptions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.exceptions import CondaError
from conda.models.channel import Channel

if TYPE_CHECKING:
    import os
    from collections.abc import Iterable
    from pathlib import Path
    from typing import Self


class CondaToSError(CondaError):
    """Base exception."""


class CondaToSMissingError(CondaToSError):
    """Error class for when the metadata is missing for a channel."""

    def __init__(self: Self, channel: str | Channel) -> None:
        """Format error message with channel base URL."""
        super().__init__(f"No Terms of Service for {_url(channel)}.")


class CondaToSInvalidError(CondaToSMissingError):
    """Error class for when the metadata is invalid for a channel."""

    def __init__(self: Self, channel: str | Channel) -> None:
        """Format error message with channel base URL."""
        super().__init__(f"Invalid Terms of Service for {_url(channel)}.")


class CondaToSPermissionError(PermissionError, CondaToSError):
    """Error class for when the metadata file cannot be written."""

    def __init__(
        self: Self,
        path: str | os.PathLike[str] | Path,
        channel: str | Channel | None = None,
    ) -> None:
        """Format error message with channel base URL and path."""
        addendum = f" for {_url(channel)}" if channel else ""
        super().__init__(
            f"Unable to read/write path ({path}){addendum}. "
            f"Please check permissions."
        )


class CondaToSRejectedError(CondaToSError):
    """Error class for when the Terms of Service are rejected for a channel."""

    def __init__(self: Self, *channels: str | Channel) -> None:
        """Format error message with channel base URL."""
        super().__init__(
            f"Terms of Service rejected for the following channels:\n"
            f"{_bullet(map(_url, channels))}\n"
            f"\n"
            f"Remove channels with rejected Terms of Service before proceeding:\n"
            f"    ‣ conda config --remove channels CHANNEL\n"
            f"\n"
            f"To accept the Terms of Service for a given channel, run the following:\n"
            f"    ‣ conda tos accept --override-channels --channel CHANNEL"
        )


class CondaToSNonInteractiveError(CondaToSError):
    """Error class when Terms of Service are not actionable in non-interactive mode."""

    def __init__(self: Self, *channels: str | Channel) -> None:
        """Format error message with channel base URL."""
        super().__init__(
            f"Terms of Service not accepted for the following channels:\n"
            f"{_bullet(map(_url, channels))}\n"
            f"\n"
            f"To accept the Terms of Service for a given channel, run the following:\n"
            f"    ‣ conda tos accept --override-channels --channel CHANNEL\n"
            f"\n"
            f"Alternatively, remove channels with rejected Terms of Services before "
            f"proceeding:\n"
            f"    ‣ conda config --remove channels CHANNEL"
        )


def _url(channel: str | Channel) -> str:
    return str(Channel(channel).base_url or channel)


def _bullet(args: Iterable[str], *, prefix: str = "    • ") -> str:
    return prefix + f"\n{prefix}".join(args)
