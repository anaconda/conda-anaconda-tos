# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS subcommand and settings plugins."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.common.configuration import PrimitiveParameter
from conda.plugins import CondaSetting, CondaSubcommand, hookimpl
from rich.console import Console
from rich.table import Table

from .tos import accept_tos, get_tos, reject_tos, view_tos

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace
    from typing import Iterator


def configure_parser(parser: ArgumentParser) -> None:
    """Configure the parser for the `tos` subcommand."""
    parser.add_argument("-c", "--channel", action="append")
    parser.add_argument("--override-channels", action="store_true")

    mutex = parser.add_mutually_exclusive_group()
    mutex.add_argument("--accept", "--agree", "--yes", action="store_true")
    mutex.add_argument(
        "--reject", "--disagree", "--no", "--withdraw", action="store_true"
    )
    mutex.add_argument("--view", "--show", action="store_true")


def accepted_mapping(
    *,
    tos_accepted: bool | None,
    acceptance_timestamp: float,
    **metadata,  # noqa: ANN003, ARG001
) -> str:
    """Map the acceptance status to a human-readable string."""
    if tos_accepted is None:
        return "not reviewed"
    elif tos_accepted:
        # convert timestamp to localized time
        return (
            datetime.utcfromtimestamp(acceptance_timestamp).astimezone().isoformat(" ")
        )
    else:
        return "rejected"


def execute(args: Namespace) -> int:
    """Execute the `tos` subcommand."""
    if args.accept:
        accept_tos(*context.channels)
    elif args.reject:
        reject_tos(*context.channels)
    elif args.view:
        view_tos(*context.channels)
    else:
        table = Table()
        table.add_column("Channel")
        table.add_column("Version")
        table.add_column("Accepted")

        for channel, metadata in get_tos(*context.channels):
            table.add_row(
                channel.base_url,
                str(metadata["tos_version"]),
                accepted_mapping(**metadata),
            )

        console = Console()
        console.print(table)
    return 0


@hookimpl
def conda_subcommands() -> Iterator[CondaSubcommand]:
    """Return a list of subcommands for the anaconda-conda-tos plugin."""
    yield CondaSubcommand(
        name="tos",
        action=execute,
        summary="View, accept, and interact with a channel's Terms of Service (ToS).",
        configure_parser=configure_parser,
    )


@hookimpl
def conda_settings() -> Iterator[CondaSetting]:
    """Return a list of settings for the anaconda-conda-tos plugin."""
    yield CondaSetting(
        name="auto_accept_tos",
        description="Automatically accept Terms of Service (ToS) for all channels.",
        parameter=PrimitiveParameter(False, element_type=bool),
    )
