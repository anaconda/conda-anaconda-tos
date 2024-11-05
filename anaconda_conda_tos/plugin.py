# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""High-level conda plugin registration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.base.context import context
from conda.cli.install import validate_prefix_exists
from conda.common.configuration import PrimitiveParameter
from conda.plugins import CondaPreCommand, CondaSetting, CondaSubcommand, hookimpl
from rich.console import Console
from rich.prompt import Prompt

from .api import accept_tos, get_channels, get_one_tos, reject_tos
from .console import render_accept, render_list, render_reject, render_view
from .exceptions import CondaToSMissingError, CondaToSRejectedError
from .models import RemoteToSMetadata
from .path import ENV_TOS_ROOT, SITE_TOS_ROOT, SYSTEM_TOS_ROOT, USER_TOS_ROOT

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace
    from collections.abc import Iterable, Iterator

    from conda.models.channel import Channel


DEFAULT_TOS_ROOT = USER_TOS_ROOT
DEFAULT_CACHE_TIMEOUT = 24 * 60 * 60


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
    for flag, value, text in (
        ("--site", SITE_TOS_ROOT, "System-wide ToS storage location."),
        ("--system", SYSTEM_TOS_ROOT, "Conda installation ToS storage location."),
        ("--user", USER_TOS_ROOT, "User ToS storage location."),
        ("--env", ENV_TOS_ROOT, "Conda environment ToS storage location."),
    ):
        location.add_argument(
            flag,
            dest="tos_root",
            action="store_const",
            const=value,
            help=text,
        )
    location.add_argument("--file", dest="tos_root", action="store")

    action_grp = parser.add_argument_group("Actions")
    action = action_grp.add_mutually_exclusive_group()
    action.add_argument("--accept", "--agree", action="store_true")
    action.add_argument("--reject", "--disagree", "--withdraw", action="store_true")
    action.add_argument("--view", "--show", action="store_true")

    parser.add_argument("--cache-timeout", action="store", type=int)
    parser.add_argument(
        "--ignore-cache",
        dest="cache_timeout",
        action="store_const",
        const=0,
    )

    parser.set_defaults(
        tos_root=DEFAULT_TOS_ROOT,
        cache_timeout=DEFAULT_CACHE_TIMEOUT,
    )


def execute(args: Namespace) -> int:
    """Execute the `tos` subcommand."""
    validate_prefix_exists(context.target_prefix)

    action = render_list
    if args.accept:
        action = render_accept
    elif args.reject:
        action = render_reject
    elif args.view:
        action = render_view

    return action(
        *context.channels,
        tos_root=args.tos_root,
        cache_timeout=args.cache_timeout,
        console=Console(),
    )


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


def _prompt_acceptance(
    channel: Channel,
    metadata: RemoteToSMetadata,
    console: Console,
    choices: Iterable[str] = ("accept", "reject", "view"),
) -> bool:
    response = Prompt.ask(
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
        return _prompt_acceptance(channel, metadata, console, ("accept", "reject"))


def _pre_command_check_tos(_command: str) -> None:
    accepted = 0
    rejected = []
    channel_metadatas = []

    console = Console()
    console.print("[bold blue]Gathering channels...")
    for channel in get_channels(*context.channels):
        try:
            metadata = get_one_tos(
                channel,
                tos_root=DEFAULT_TOS_ROOT,
                cache_timeout=DEFAULT_CACHE_TIMEOUT,
            ).metadata
        except CondaToSMissingError:
            # CondaToSMissingError: no ToS metadata found
            continue

        if type(metadata) is RemoteToSMetadata:
            # ToS hasn't been accepted or rejected yet
            channel_metadatas.append((channel, metadata))
        elif metadata.tos_accepted:
            accepted += 1
        else:
            rejected.append(channel)

    if rejected:
        console.print(f"[bold red]{len(rejected)} channel ToS rejected")
        raise CondaToSRejectedError(*rejected)

    console.print("[bold yellow]Reviewing channels...")
    for channel, metadata in channel_metadatas:
        if context.plugins.auto_accept_tos or _prompt_acceptance(
            channel, metadata, console
        ):
            accept_tos(
                channel, tos_root=DEFAULT_TOS_ROOT, cache_timeout=DEFAULT_CACHE_TIMEOUT
            )
            accepted += 1
        else:
            reject_tos(
                channel, tos_root=DEFAULT_TOS_ROOT, cache_timeout=DEFAULT_CACHE_TIMEOUT
            )
            rejected.append(channel)

    if rejected:
        console.print(f"[bold red]{len(rejected)} channel ToS rejected")
        raise CondaToSRejectedError(*rejected)
    console.print(f"[bold green]{accepted} channel ToS accepted")


@hookimpl(tryfirst=True)
def conda_pre_commands() -> Iterator[CondaPreCommand]:
    """Return a list of pre-commands for the anaconda-conda-tos plugin."""
    yield CondaPreCommand(
        name="check_tos",
        action=_pre_command_check_tos,
        run_for={
            "create",
            "env_create",
            "env_remove",
            "env_update",
            "install",
            "remove",
            "update",
        },
    )
