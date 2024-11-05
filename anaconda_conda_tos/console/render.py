# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Render functions for console output."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

from ..api import accept_tos, get_channels, get_tos, reject_tos
from ..exceptions import CondaToSMissingError
from ..remote import get_metadata
from .mappers import accepted_mapping, location_mapping

if TYPE_CHECKING:
    import os
    from pathlib import Path

    from conda.models.channel import Channel


def render_list(*channels: str | Channel) -> None:
    """Printout listing of unaccepted, accepted, and rejected ToS."""
    table = Table()
    table.add_column("Channel")
    table.add_column("Version")
    table.add_column("Accepted")
    table.add_column("Location")

    for channel, metadata_pair in get_tos(*channels):
        if not metadata_pair:
            table.add_row(channel.base_url, "-", "-", "-")
        else:
            table.add_row(
                channel.base_url,
                str(metadata_pair.metadata.tos_version),
                accepted_mapping(metadata_pair.metadata),
                location_mapping(metadata_pair.path),
            )

    console = Console()
    console.print(table)


def render_view(*channels: str | Channel) -> None:
    """Print the ToS full text for the given channels."""
    for channel in get_channels(*channels):
        print(f"viewing ToS for {channel}:")
        try:
            print(get_metadata(channel).text)
        except CondaToSMissingError:
            print("ToS not found")


def render_accept(*channels: str | Channel, tos_root: str | os.PathLike | Path) -> None:
    """Accept the ToS for the given channels."""
    for channel in get_channels(*channels):
        try:
            accept_tos(tos_root, channel)
        except CondaToSMissingError:
            print(f"ToS not found for {channel}")
        else:
            print(f"accepted ToS for {channel}")


def render_reject(*channels: str | Channel, tos_root: str | os.PathLike | Path) -> None:
    """Reject the ToS for the given channels."""
    for channel in get_channels(*channels):
        try:
            reject_tos(tos_root, channel)
        except CondaToSMissingError:
            print(f"ToS not found for {channel}")
        else:
            print(f"rejected ToS for {channel}")
