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
from ..exceptions import CondaToSMissingError, CondaToSRejectedError
from ..models import RemoteToSMetadata
from .mappers import accepted_mapping, location_mapping, timestamp_mapping
from .prompt import FuzzyPrompt

if TYPE_CHECKING:
    import os
    from collections.abc import Iterable
    from pathlib import Path

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
                timestamp_mapping(metadata_pair.metadata.timestamp),
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


def _prompt_acceptance(
    channel: Channel,
    metadata: RemoteToSMetadata,
    console: Console,
    choices: Iterable[str] = ("(a)ccept", "(r)eject", "(v)iew"),
) -> bool:
    response = FuzzyPrompt.ask(
        f"Accept the Terms of Service (ToS) for this channel ({channel})?",
        choices=choices,
        console=console,
    )
    if response == "accept":
        return True
    elif response == "reject":
        return False
    else:
        console.print(metadata.text)
        return _prompt_acceptance(channel, metadata, console, ("(a)ccept", "(r)eject"))


def render_interactive(
    *channels: str | Channel,
    tos_root: str | os.PathLike | Path,
    cache_timeout: int | float | None,
    console: Console | None = None,
    auto_accept_tos: bool,
) -> int:
    """Prompt user to accept or reject ToS for channels."""
    accepted = 0
    rejected = []
    channel_metadatas = []

    console = console or Console()
    console.print("[bold blue]Gathering channels...")
    for channel in get_channels(*channels):
        try:
            metadata = get_one_tos(
                channel, tos_root=tos_root, cache_timeout=cache_timeout
            ).metadata
        except CondaToSMissingError:
            # CondaToSMissingError: no ToS metadata found
            continue

        if isinstance(metadata, RemoteToSMetadata):
            # ToS hasn't been accepted or rejected yet
            channel_metadatas.append((channel, metadata))
        elif metadata.tos_accepted:
            accepted += 1
        else:
            rejected.append(channel)

    console.print("[bold yellow]Reviewing channels...")
    if rejected:
        console.print(f"[bold red]{len(rejected)} channel ToS rejected")
        raise CondaToSRejectedError(*rejected)

    for channel, metadata in channel_metadatas:
        if auto_accept_tos or _prompt_acceptance(channel, metadata, console):
            accept_tos(channel, tos_root=tos_root, cache_timeout=cache_timeout)
            accepted += 1
        else:
            reject_tos(channel, tos_root=tos_root, cache_timeout=cache_timeout)
            rejected.append(channel)

    if rejected:
        console.print(f"[bold red]{len(rejected)} channel ToS rejected")
        raise CondaToSRejectedError(*rejected)
    console.print(f"[bold green]{accepted} channel ToS accepted")
    return 0
