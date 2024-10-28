# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS subcommand and settings plugins."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.base.context import context
from conda.cli.install import validate_prefix_exists
from conda.common.configuration import PrimitiveParameter
from conda.plugins import CondaSetting, CondaSubcommand, hookimpl
from rich.console import Console
from rich.table import Table

from .path import SYSTEM_TOS_ROOT, USER_TOS_ROOT
from .tos import accept_tos, get_tos, reject_tos, view_tos

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace
    from pathlib import Path
    from typing import Iterator

    from .metadata import ToSMetadata


def configure_parser(parser: ArgumentParser) -> None:
    """Configure the parser for the `tos` subcommand."""
    parser.add_argument("-c", "--channel", action="append")
    parser.add_argument("--override-channels", action="store_true")

    prefix_grp = parser.add_argument_group("Conda Environment")
    prefix = prefix_grp.add_mutually_exclusive_group()
    prefix.add_argument("-n", "--name")
    prefix.add_argument("-p", "--prefix")

    location_grp = parser.add_argument_group("Local ToS Storage Location")
    location = location_grp.add_mutually_exclusive_group()
    location.add_argument(
        "--system", dest="tos_root", const=SYSTEM_TOS_ROOT, action="store_const"
    )
    location.add_argument(
        "--user", dest="tos_root", const=USER_TOS_ROOT, action="store_const"
    )
    location.add_argument("--file", dest="tos_root", action="store")
    parser.set_defaults(tos_root=USER_TOS_ROOT)

    action_grp = parser.add_argument_group("Actions")
    action = action_grp.add_mutually_exclusive_group()
    action.add_argument("--accept", "--agree", action="store_true")
    action.add_argument("--reject", "--disagree", "--withdraw", action="store_true")
    action.add_argument("--view", "--show", action="store_true")


def version_mapping(metadata: ToSMetadata | None) -> str:
    """Map the ToS version to a human-readable string."""
    return str(metadata.tos_version) if metadata else "-"


def accepted_mapping(metadata: ToSMetadata | None) -> str:
    """Map the ToS acceptance status to a human-readable string."""
    if metadata is None:
        return "-"
    elif metadata.tos_accepted:
        # convert timestamp to localized time
        return metadata.acceptance_timestamp.astimezone().isoformat(" ")
    else:
        return "rejected"


def path_mapping(path: Path | None) -> str:
    """Map the ToS path to a human-readable string."""
    return str(path.parent.parent) if path else "-"


def execute(args: Namespace) -> int:
    """Execute the `tos` subcommand."""
    validate_prefix_exists(context.target_prefix)

    if args.accept:
        accept_tos(args.tos_root, *context.channels)
    elif args.reject:
        reject_tos(args.tos_root, *context.channels)
    elif args.view:
        view_tos(*context.channels)
    else:
        table = Table()
        table.add_column("Channel")
        table.add_column("Version")
        table.add_column("Accepted")
        table.add_column("Location")

        for channel, metadata, path in get_tos(*context.channels):
            table.add_row(
                channel.base_url,
                version_mapping(metadata),
                accepted_mapping(metadata),
                path_mapping(path),
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
