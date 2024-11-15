# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Render functions for console output."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from conda.exceptions import ArgumentError
from rich.console import Console
from rich.table import Table

from ..api import (
    CI,
    accept_tos,
    clean_cache,
    clean_tos,
    get_all_tos,
    get_channels,
    get_one_tos,
    reject_tos,
)
from ..exceptions import CondaToSMissingError, CondaToSRejectedError
from ..models import RemoteToSMetadata
from ..path import CACHE_DIR, SEARCH_PATH
from .mappers import accepted_mapping, location_mapping, timestamp_mapping
from .prompt import FuzzyPrompt

if TYPE_CHECKING:
    import os
    from collections.abc import Iterable

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
    table.add_column("Support")

    for channel, metadata_pair in get_all_tos(
        *channels,
        tos_root=tos_root,
        cache_timeout=cache_timeout,
    ):
        if not metadata_pair:
            table.add_row(channel.base_url, "-", "-", "-", "-")
        else:
            table.add_row(
                channel.base_url,
                timestamp_mapping(metadata_pair.metadata.version),
                accepted_mapping(metadata_pair.metadata),
                location_mapping(metadata_pair.path),
                metadata_pair.metadata.support,
            )

    console = console or Console()
    console.print(table)
    return 0


def render_view(
    *channels: str | Channel,
    tos_root: str | os.PathLike[str] | Path,
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
    tos_root: str | os.PathLike[str] | Path,
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
    tos_root: str | os.PathLike[str] | Path,
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


def _gather_tos(
    *channels: str | Channel,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int | float | None,
) -> tuple[list[Channel], list[Channel], list[tuple[Channel, RemoteToSMetadata]]]:
    accepted = []
    rejected = []
    channel_metadatas = []
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
            accepted.append(channel)
        else:
            rejected.append(channel)
    return accepted, rejected, channel_metadatas


def render_interactive(
    *channels: str | Channel,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int | float | None,
    console: Console | None = None,
    auto_accept_tos: bool,
) -> int:
    """Prompt user to accept or reject ToS for channels."""
    console = console or Console()
    console.print("[bold blue]Gathering channels...")
    accepted, rejected, channel_metadatas = _gather_tos(
        *channels,
        tos_root=tos_root,
        cache_timeout=cache_timeout,
    )

    console.print("[bold yellow]Reviewing channels...")
    if rejected:
        console.print(f"[bold red]{len(rejected)} channel ToS rejected")
        raise CondaToSRejectedError(*rejected)

    if CI:
        console.print("[bold yellow]CI detected...")

    for channel, metadata in channel_metadatas:
        if auto_accept_tos:
            # auto_accept_tos overrides any other setting
            accept_tos(channel, tos_root=tos_root, cache_timeout=cache_timeout)
            accepted.append(channel)
        elif CI:
            # CI is the same as auto_accept_tos but with a warning
            console.print(f"[bold yellow]implicitly accepting ToS for {channel}")
            accept_tos(channel, tos_root=tos_root, cache_timeout=cache_timeout)
            accepted.append(channel)
        elif _prompt_acceptance(channel, metadata, console):
            # user manually accepted the ToS
            accept_tos(channel, tos_root=tos_root, cache_timeout=cache_timeout)
            accepted.append(channel)
        else:
            # user manually rejected the ToS
            reject_tos(channel, tos_root=tos_root, cache_timeout=cache_timeout)
            rejected.append(channel)

    if rejected:
        console.print(f"[bold red]{len(rejected)} channel ToS rejected")
        raise CondaToSRejectedError(*rejected)
    console.print(f"[bold green]{len(accepted)} channel ToS accepted")
    return 0


def render_info(*, console: Console | None = None) -> int:
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


def render_clean(
    cache: bool,
    tos: bool,
    all: bool,  # noqa: A002
    *,
    tos_root: str | os.PathLike[str] | Path,
    console: Console | None = None,
) -> int:
    """Clean the ToS cache directories."""
    if not (all or cache or tos):
        raise ArgumentError(
            "At least one removal target must be given. See 'conda tos clean --help'."
        )

    console = console or Console()
    if all or cache:
        console.print(f"Removed {len(list(clean_cache()))} cache files.")
    if all or tos:
        console.print(f"Removed {len(list(clean_tos(tos_root)))} ToS files.")
    return 0
