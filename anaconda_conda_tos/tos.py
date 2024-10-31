# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS management functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.models.channel import Channel
from rich.console import Console
from rich.progress import track
from rich.table import Table

from .cache import get_all_metadatas, get_metadata
from .exceptions import CondaToSMissingError
from .local import write_metadata
from .path import CACHE_DIR, SEARCH_PATH, get_all_channel_paths, get_cache_paths

if TYPE_CHECKING:
    import os
    from pathlib import Path
    from typing import Iterable, Iterator

    from .models import MetadataPathPair


def get_channels(*channels: str | Channel) -> Iterable[Channel]:
    """Yield all unique channels from the given channels."""
    # expand every multichannel into its individual channels
    # and remove any duplicates
    seen: set[Channel] = set()
    for multichannel in map(Channel, channels):
        for channel in map(Channel, multichannel.urls()):
            channel = Channel(channel.base_url)
            if channel not in seen:
                yield channel
                seen.add(channel)


def view_tos(
    *channels: str | Channel,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int,
) -> None:
    """Print the ToS full text for the given channels."""
    for channel in get_channels(*channels):
        print(f"viewing ToS for {channel}:")
        try:
            metadata_pair = get_metadata(tos_root, channel, cache_timeout)
            print(metadata_pair.metadata.text)
        except CondaToSMissingError:
            print("ToS not found")


def accept_tos(
    *channels: str | Channel,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int,
) -> None:
    """Accept the ToS for the given channels."""
    for channel in get_channels(*channels):
        try:
            metadata_pair = get_metadata(tos_root, channel, cache_timeout)
        except CondaToSMissingError:
            print(f"ToS not found for {channel}")
        else:
            print(f"accepting ToS for {channel}")
            write_metadata(tos_root, channel, metadata_pair.metadata, tos_accepted=True)


def reject_tos(
    *channels: str | Channel,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int,
) -> None:
    """Reject the ToS for the given channels."""
    for channel in get_channels(*channels):
        try:
            metadata_pair = get_metadata(tos_root, channel, cache_timeout)
        except CondaToSMissingError:
            print(f"ToS not found for {channel}")
        else:
            print(f"rejecting ToS for {channel}")
            write_metadata(
                tos_root, channel, metadata_pair.metadata, tos_accepted=False
            )


def get_tos(
    *channels: str | Channel,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int,
) -> Iterator[tuple[Channel, MetadataPathPair | None]]:
    """List all channels and whether their ToS has been accepted."""
    # list all active channels
    seen: set[Channel] = set()
    for channel in get_channels(*channels):
        try:
            yield channel, get_metadata(tos_root, channel, cache_timeout)
        except CondaToSMissingError:
            yield channel, None
        seen.add(channel)

    # list all other ToS that have been accepted/rejected
    for channel, metadata_pair in get_all_metadatas(tos_root, cache_timeout):
        if channel not in seen:
            yield channel, metadata_pair
            seen.add(channel)


def info_tos() -> None:
    """Print ToS information."""
    table = Table(show_header=False)
    table.add_column("Key")
    table.add_column("Value")

    table.add_row("Search Path", "\n".join(SEARCH_PATH))
    table.add_row("Cache Dir", str(CACHE_DIR))

    console = Console()
    console.print(table)


def clean_cache() -> None:
    """Remove the ToS cache."""
    paths = tuple(get_cache_paths())
    if not paths:
        return

    for cache in track(paths, description="Deleting Cache"):
        if cache.is_file():
            cache.unlink()


def clean_tos() -> None:
    """Remove the ToS files."""
    paths = tuple(get_all_channel_paths())
    if not paths:
        return

    for tos in track(paths, description="Deleting ToS"):
        if tos.is_file():
            tos.unlink()


def version_mapping(metadata_pair: MetadataPathPair | None) -> str:
    """Map the ToS version to a human-readable string."""
    if not metadata_pair or not metadata_pair.metadata:
        return "-"
    return str(metadata_pair.metadata.tos_version)


def accepted_mapping(metadata_pair: MetadataPathPair | None) -> str:
    """Map the ToS acceptance status to a human-readable string."""
    if (
        not metadata_pair
        or not metadata_pair.metadata
        or (tos_accepted := metadata_pair.metadata.tos_accepted) is None
    ):
        return "-"
    elif tos_accepted:
        if (
            acceptance_timestamp := metadata_pair.metadata.acceptance_timestamp
        ) is None:
            return "unknown"
        else:
            # convert timestamp to localized time
            return acceptance_timestamp.astimezone().isoformat(" ")
    else:
        return "rejected"


def location_mapping(metadata_pair: MetadataPathPair | None) -> str:
    """Map the ToS path to a human-readable string."""
    if not metadata_pair or not metadata_pair.path:
        return "-"
    return str(metadata_pair.path.parent.parent)


def list_tos(
    *channels: str | Channel,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int,
) -> None:
    """List all channels and whether their ToS has been accepted."""
    table = Table()
    table.add_column("Channel")
    table.add_column("Version")
    table.add_column("Accepted")
    table.add_column("Location")

    for channel, metadata_pair in get_tos(
        *channels,
        tos_root=tos_root,
        cache_timeout=cache_timeout,
    ):
        table.add_row(
            channel.base_url,
            version_mapping(metadata_pair),
            accepted_mapping(metadata_pair),
            location_mapping(metadata_pair),
        )

    console = Console()
    console.print(table)
