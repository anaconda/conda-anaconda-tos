# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Custom exceptions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.exceptions import CondaError
from conda.models.channel import Channel

if TYPE_CHECKING:
    import os
    from pathlib import Path
    from typing import Self


class CondaToSError(CondaError):
    """Base exception."""


class CondaToSMissingError(CondaToSError):
    """Error class for when the metadata is missing for a channel."""

    def __init__(self: Self, channel: str | Channel) -> None:
        """Format error message with channel base URL."""
        super().__init__(
            f"No Terms of Service for {Channel(channel).base_url or channel}."
        )


class CondaToSInvalidError(CondaToSMissingError):
    """Error class for when the metadata is invalid for a channel."""

    def __init__(self: Self, channel: str | Channel) -> None:
        """Format error message with channel base URL."""
        super().__init__(
            f"Invalid Terms of Service for {Channel(channel).base_url or channel}."
        )


class CondaToSPermissionError(PermissionError, CondaToSError):
    """Error class for when the metadata file cannot be written."""

    def __init__(
        self: Self,
        path: str | os.PathLike[str] | Path,
        channel: str | Channel | None = None,
    ) -> None:
        """Format error message with channel base URL and path."""
        addendum = f" for {Channel(channel).base_url or channel}" if channel else ""
        super().__init__(
            f"Unable to read/write path ({path}){addendum}. "
            "Please check permissions."
        )


class CondaToSRejectedError(CondaToSError):
    """Error class for when the Terms of Service are rejected for a channel."""

    def __init__(self: Self, *channels: str | Channel) -> None:
        """Format error message with channel base URL."""
        channels_str = ", ".join(
            str(Channel(channel).base_url or channel) for channel in channels
        )
        super().__init__(f"Terms of Service rejected for {channels_str}.")


class CondaToSNonInteractiveError(CondaToSError):
    """Error class when Terms of Service are not actionable in non-interactive mode."""

    def __init__(self: Self, *channels: str | Channel) -> None:
        """Format error message with channel base URL."""
        channels_str = ", ".join(
            str(Channel(channel).base_url or channel) for channel in channels
        )
        super().__init__(
            f"Terms of Service not actionable for {channels_str} in "
            f"non-interactive mode."
        )
