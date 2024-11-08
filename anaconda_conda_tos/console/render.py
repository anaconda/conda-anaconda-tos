# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Render functions for console output."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

from ..api import (
    accept_tos,
    get_all_tos,
    get_channels,
    get_one_tos,
    reject_tos,
)
from ..exceptions import CondaToSMissingError
from ..path import CACHE_DIR, SEARCH_PATH
from .mappers import accepted_mapping, location_mapping

if TYPE_CHECKING:
    import os

    from conda.models.channel import Channel


def render_list(
    *channels: str | Channel,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int | float | None,
    console: Console | None = None,
) -> int:
    """Display listing of unaccepted, accepted, and rejected ToS."""
    table = Table()
    table.add_column("Channel")
    table.add_column("Version")
    table.add_column("Accepted")
    table.add_column("Location")

    for channel, metadata_pair in get_all_tos(
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

    console = console or Console()
    console.print(table)
    return 0


def render_view(
    *channels: str | Channel,
    tos_root: str | os.PathLike | Path,
    cache_timeout: int | float | None,
    console: Console | None = None,
) -> int:
    """Display the ToS text for the given channels."""
    console = console or Console()
    for channel in get_channels(*channels):
        try:
            metadata = get_one_tos(
                channel, tos_root=tos_root, cache_timeout=cache_timeout
            ).metadata
        except CondaToSMissingError:
            console.print(f"no ToS for {channel}")
        else:
            console.print(f"viewing ToS for {channel}:")
            console.print(metadata.text)
    return 0


def render_accept(
    *channels: str | Channel,
    tos_root: str | os.PathLike | Path,
    cache_timeout: int | float | None,
    console: Console | None = None,
) -> int:
    """Display acceptance of the ToS for the given channels."""
    console = console or Console()
    for channel in get_channels(*channels):
        try:
            accept_tos(channel, tos_root=tos_root, cache_timeout=cache_timeout)
        except CondaToSMissingError:
            console.print(f"ToS not found for {channel}")
        else:
            console.print(f"accepted ToS for {channel}")
    return 0


def render_reject(
    *channels: str | Channel,
    tos_root: str | os.PathLike | Path,
    cache_timeout: int | float | None,
    console: Console | None = None,
) -> int:
    """Display rejection of the ToS for the given channels."""
    console = console or Console()
    for channel in get_channels(*channels):
        try:
            reject_tos(channel, tos_root=tos_root, cache_timeout=cache_timeout)
        except CondaToSMissingError:
            console.print(f"ToS not found for {channel}")
        else:
            console.print(f"rejected ToS for {channel}")
    return 0


def render_info(console: Console | None = None) -> int:
    """Display information about the ToS cache."""
    table = Table(show_header=False)
    table.add_column("Key")
    table.add_column("Value")

    table.add_row("SEARCH_PATH", "\n".join(SEARCH_PATH))
    try:
        relative_dir = Path("~", CACHE_DIR.relative_to(Path.home()))
    except ValueError:
        # ValueError: CACHE_DIR is not relative to the user's home directory
        relative_dir = CACHE_DIR
    table.add_row("CACHE_DIR", str(relative_dir))

    console = console or Console()
    console.print(table)

    return 0
