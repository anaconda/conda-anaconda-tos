# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Render functions for console output."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

from ..tos import get_tos
from .mappers import accepted_mapping, location_mapping, version_mapping

if TYPE_CHECKING:
    from conda.models.channel import Channel


def list_tos(*channels: str | Channel) -> None:
    """Printout listing of unaccepted, accepted, and rejected ToS."""
    table = Table()
    table.add_column("Channel")
    table.add_column("Version")
    table.add_column("Accepted")
    table.add_column("Location")

    for channel, metadata_pair in get_tos(*channels):
        table.add_row(
            channel.base_url,
            version_mapping(metadata_pair),
            accepted_mapping(metadata_pair),
            location_mapping(metadata_pair),
        )

    console = Console()
    console.print(table)
