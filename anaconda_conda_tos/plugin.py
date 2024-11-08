# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""High-level conda plugin registration."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.cli.install import validate_prefix_exists
from conda.common.configuration import PrimitiveParameter
from conda.plugins import (
    CondaPreCommand,
    CondaRequestHeader,
    CondaSetting,
    CondaSubcommand,
    hookimpl,
)
from rich.console import Console

from .api import get_active_tos
from .console import (
    render_accept,
    render_interactive,
    render_list,
    render_reject,
    render_view,
)
from .models import LocalPair
from .path import ENV_TOS_ROOT, SITE_TOS_ROOT, SYSTEM_TOS_ROOT, USER_TOS_ROOT

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace
    from collections.abc import Iterator
    from typing import Callable


#: Default ToS storage location.
DEFAULT_TOS_ROOT = USER_TOS_ROOT

#: Default cache timeout in seconds.
DEFAULT_CACHE_TIMEOUT = timedelta(days=1).total_seconds()

#: Field separator for request header
FIELD_SEPARATOR = ";"

#: Key-value separator for request header
KEY_SEPARATOR = "="


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
    action.add_argument("--interactive", action="store_true")

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

    action: Callable = render_list
    kwargs = {}
    if args.accept:
        action = render_accept
    elif args.reject:
        action = render_reject
    elif args.view:
        action = render_view
    elif args.interactive:
        action = render_interactive
        kwargs["auto_accept_tos"] = context.plugins.auto_accept_tos

    return action(
        *context.channels,
        tos_root=args.tos_root,
        cache_timeout=args.cache_timeout,
        console=Console(),
        **kwargs,
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


def _pre_command_check_tos(_command: str) -> None:
    render_interactive(
        *context.channels,
        tos_root=DEFAULT_TOS_ROOT,
        cache_timeout=DEFAULT_CACHE_TIMEOUT,
        auto_accept_tos=context.plugins.auto_accept_tos,
    )


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
            "search",
            "update",
        },
    )


def _format_active_channels_tos() -> Iterator[tuple[str, int, str, int]]:
    for channel, metadata_pair in get_active_tos(
        *context.channels,
        tos_root=DEFAULT_TOS_ROOT,
        cache_timeout=DEFAULT_CACHE_TIMEOUT,
    ):
        if not metadata_pair:
            continue

        tos_accepted = "unknown"
        acceptance_timestamp = 0
        if isinstance(metadata_pair, LocalPair):
            metadata = metadata_pair.metadata
            tos_accepted = "accepted" if metadata.tos_accepted else "rejected"
            acceptance_timestamp = int(metadata.acceptance_timestamp.timestamp())
        yield (
            channel.base_url,
            int(metadata_pair.metadata.timestamp.timestamp()),
            tos_accepted,
            acceptance_timestamp,
        )


@hookimpl
def conda_request_headers() -> Iterator[CondaRequestHeader]:
    """Return a list of request headers for the anaconda-conda-tos plugin."""
    yield CondaRequestHeader(
        name="Anaconda-ToS-Accept",
        description="Header which specifies when the user has accepted the ToS",
        value=FIELD_SEPARATOR.join(
            KEY_SEPARATOR.join(map(str, keys)) for keys in _format_active_channels_tos()
        ),
        hosts={"repo.anaconda.com"},
    )
