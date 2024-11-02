# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Render functions for console output."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

from ..api import get_all_metadatas
from ..path import CACHE_DIR, SEARCH_PATH
from .mappers import accepted_mapping, location_mapping

if TYPE_CHECKING:
    import os

    from conda.models.channel import Channel


def list_tos(
    *channels: str | Channel,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int | float | None,
) -> None:
    """Printout listing of unaccepted, accepted, and rejected ToS."""
    table = Table()
    table.add_column("Channel")
    table.add_column("Version")
    table.add_column("Accepted")
    table.add_column("Location")

    for channel, metadata_pair in get_all_metadatas(
        *channels,
        tos_root=tos_root,
        cache_timeout=cache_timeout,
    ):
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


def info_tos() -> None:
    """Printout information for ToS plugin."""
    table = Table(show_header=False)
    table.add_column("Key")
    table.add_column("Value")

    table.add_row("Search Path", "\n".join(SEARCH_PATH))

    try:
        relative_cache_dir = Path("~", CACHE_DIR.relative_to(Path.home()))
    except ValueError:
        # ValueError: path is not within the home directory
        relative_cache_dir = CACHE_DIR

    table.add_row("Cache Dir", str(relative_cache_dir))

    console = Console()
    console.print(table)
