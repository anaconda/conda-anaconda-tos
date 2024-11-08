# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""High-level conda plugin registration."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.cli.install import validate_prefix_exists
from conda.common.configuration import PrimitiveParameter
from conda.plugins import CondaPreCommand, CondaSetting, CondaSubcommand, hookimpl
from rich.console import Console

from .console import (
    render_accept,
    render_info,
    render_interactive,
    render_list,
    render_reject,
    render_view,
)
from .path import ENV_TOS_ROOT, SITE_TOS_ROOT, SYSTEM_TOS_ROOT, USER_TOS_ROOT

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace
    from collections.abc import Iterator
    from typing import Callable


#: Default ToS storage location.
DEFAULT_TOS_ROOT = USER_TOS_ROOT

#: Default cache timeout in seconds.
DEFAULT_CACHE_TIMEOUT = timedelta(days=1).total_seconds()


def configure_parser(parser: ArgumentParser) -> None:
    """Configure the parser for the `tos` subcommand."""
    parser.add_argument(
        "-c",
        "--channel",
        action="append",
        help="Additional channels to search for ToS.",
    )
    parser.add_argument(
        "--override-channels",
        action="store_true",
        help="Do not search default or .condarc channels. Requires --channel.",
    )

    prefix_grp = parser.add_argument_group("Conda Environment")
    prefix = prefix_grp.add_mutually_exclusive_group()
    prefix.add_argument("-n", "--name", help="Name of environment.")
    prefix.add_argument(
        "-p",
        "--prefix",
        help="Full path to environment location (i.e. prefix).",
    )

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
    location.add_argument(
        "--tos-root",
        action="store",
        help="Custom ToS storage location.",
    )

    action_grp = parser.add_argument_group("Actions")
    action = action_grp.add_mutually_exclusive_group()
    action.add_argument(
        "--accept",
        action="store_true",
        help=(
            "Accept the ToS for all active channels "
            "(default, .condarc, and/or those specified via --channel)."
        ),
    )
    action.add_argument(
        "--reject",
        action="store_true",
        help=(
            "Reject the ToS for all active channels "
            "(default, .condarc, and/or those specified via --channel)."
        ),
    )
    action.add_argument(
        "--view",
        action="store_true",
        help=(
            "View the ToS for all active channels "
            "(default, .condarc, and/or those specified via --channel)."
        ),
    )
    action.add_argument(
        "--interactive",
        action="store_true",
        help=(
            "Interactively accept/reject/view ToS for all active channels "
            "(default, .condarc, and/or those specified via --channel)."
        ),
    )
    action.add_argument(
        "--info",
        action="store_true",
        help="Display information about the ToS plugin "
        "(e.g., search path and cache directory).",
    )

    parser.add_argument(
        "--cache-timeout",
        action="store",
        type=int,
        help="Cache timeout (in seconds) to check for ToS updates.",
    )
    parser.add_argument(
        "--ignore-cache",
        dest="cache_timeout",
        action="store_const",
        const=0,
        help="Ignore the cache and always check for ToS updates.",
    )

    parser.set_defaults(
        tos_root=DEFAULT_TOS_ROOT,
        cache_timeout=DEFAULT_CACHE_TIMEOUT,
    )


def execute(args: Namespace) -> int:
    """Execute the `tos` subcommand."""
    validate_prefix_exists(context.target_prefix)

    console = Console()
    if args.info:
        # refactor into `conda info` plugin (when possible)
        return render_info(console)

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
        console=console,
        **kwargs,
    )


@hookimpl
def conda_subcommands() -> Iterator[CondaSubcommand]:
    """Return a list of subcommands for the anaconda-conda-tos plugin."""
    yield CondaSubcommand(
        name="tos",
        action=execute,
        summary=(
            "A subcommand for viewing, accepting, rejecting, and otherwise interacting "
            "with a channel's Terms of Service (ToS). This plugin periodically checks "
            "for updated ToS for the active/selected channels. Channels with a ToS "
            "will need to be accepted or rejected prior to use. Conda will only allow "
            "package installation from channels without a ToS or with an accepted ToS. "
            "Attempting to use a channel with a reject ToS will result in an error."
        ),
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
            "update",
        },
    )
