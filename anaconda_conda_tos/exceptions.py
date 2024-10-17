# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS exceptions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.exceptions import CondaError
from conda.models.channel import Channel

if TYPE_CHECKING:
    from typing import Self


class CondaToSError(CondaError):
    """Base class for anaconda-conda-tos errors."""


class CondaToSMissingError(CondaToSError):
    """Error class for when the ToS is missing for a channel."""

    def __init__(self: Self, channel: str | Channel) -> None:
        """Format error message with channel base URL."""
        super().__init__(f"No ToS for {Channel(channel).base_url or channel}.")
