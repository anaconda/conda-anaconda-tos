# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""High-level conda plugin registration."""

from __future__ import annotations

from datetime import timedelta
from functools import cache
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.cli.helpers import add_parser_prefix
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

from . import APP_NAME, APP_VERSION
from .api import CI, get_channels
from .console import (
    render_accept,
    render_clean,
    render_info,
    render_interactive,
    render_list,
    render_reject,
    render_view,
)
from .exceptions import CondaToSMissingError
from .local import get_local_metadata
from .path import ENV_TOS_ROOT, SITE_TOS_ROOT, SYSTEM_TOS_ROOT, USER_TOS_ROOT
from .remote import ENDPOINT

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

#: Hosts to which the ToS header is added
HOSTS = {"repo.anaconda.com"}


def _add_channel(parser: ArgumentParser) -> None:
    channel_group = parser.add_argument_group("Channel Customization")
    channel_group.add_argument(
        "-c",
        "--channel",
        action="append",
        help="Additional channels to search for ToS.",
    )
    channel_group.add_argument(
        "--override-channels",
        action="store_true",
        help="Do not search default or .condarc channels. Requires --channel.",
    )


def _add_location(parser: ArgumentParser) -> None:
    location_group = parser.add_argument_group("Local ToS Storage Location")
    location_mutex = location_group.add_mutually_exclusive_group()
    for flag, value, text in (
        ("--site", SITE_TOS_ROOT, "System-wide ToS storage location."),
        ("--system", SYSTEM_TOS_ROOT, "Conda installation ToS storage location."),
        ("--user", USER_TOS_ROOT, "User ToS storage location."),
        ("--env", ENV_TOS_ROOT, "Conda environment ToS storage location."),
    ):
        location_mutex.add_argument(
            flag,
            dest="tos_root",
            action="store_const",
            const=value,
            help=text,
        )
    location_mutex.add_argument(
        "--tos-root",
        action="store",
        help="Custom ToS storage location.",
    )
    parser.set_defaults(tos_root=DEFAULT_TOS_ROOT)


def _add_cache(parser: ArgumentParser) -> None:
    cache_group = parser.add_argument_group("Cache Control")
    cache_mutex = cache_group.add_mutually_exclusive_group()
    cache_mutex.add_argument(
        "--cache-timeout",
        action="store",
        type=int,
        help="Cache timeout (in seconds) to check for ToS updates.",
    )
    cache_mutex.add_argument(
        "--ignore-cache",
        dest="cache_timeout",
        action="store_const",
        const=0,
        help="Ignore the cache and always check for ToS updates.",
    )
    parser.set_defaults(cache_timeout=DEFAULT_CACHE_TIMEOUT)


def configure_parser(parser: ArgumentParser) -> None:
    """Configure the parser for the `tos` subcommand."""
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"{APP_NAME} {APP_VERSION}",
        help=f"Show the {APP_NAME} version number and exit.",
    )

    subparsers = parser.add_subparsers(
        title="subcommand",
        description="The following subcommands are available.",
        dest="cmd",
        required=False,
    )

    accept_parser = subparsers.add_parser(
        "accept",
        help=(
            "Accept the ToS for all active channels "
            "(default, .condarc, and/or those specified via --channel)."
        ),
    )
    _add_channel(accept_parser)
    add_parser_prefix(accept_parser)
    _add_location(accept_parser)
    _add_cache(accept_parser)

    reject_parser = subparsers.add_parser(
        "reject",
        help=(
            "Reject the ToS for all active channels "
            "(default, .condarc, and/or those specified via --channel)."
        ),
    )
    _add_channel(reject_parser)
    add_parser_prefix(reject_parser)
    _add_location(reject_parser)
    _add_cache(reject_parser)

    view_parser = subparsers.add_parser(
        "view",
        help=(
            "View the ToS for all active channels "
            "(default, .condarc, and/or those specified via --channel)."
        ),
    )
    _add_channel(view_parser)
    add_parser_prefix(view_parser)
    _add_location(view_parser)
    _add_cache(view_parser)

    interactive_parser = subparsers.add_parser(
        "interactive",
        help=(
            "Interactively accept/reject/view ToS for all active channels "
            "(default, .condarc, and/or those specified via --channel)."
        ),
    )
    _add_channel(interactive_parser)
    add_parser_prefix(interactive_parser)
    _add_location(interactive_parser)
    _add_cache(interactive_parser)

    subparsers.add_parser(
        "info",
        help=(
            "Display information about the ToS plugin "
            "(e.g., search path and cache directory)."
        ),
    )

    # default behavior (listing current ToS statuses) arguments
    _add_channel(parser)
    add_parser_prefix(parser)
    _add_location(parser)
    _add_cache(parser)

    clean_parser = subparsers.add_parser(
        "clean",
        help="Clean the ToS cache directories.",
    )
    clean_parser.add_argument(
        "--cache",
        action="store_true",
        help="Remove all ToS cache files.",
    )
    clean_parser.add_argument(
        "--tos",
        action="store_true",
        help="Remove all ToS acceptances/rejections.",
    )
    clean_parser.add_argument(
        "--all",
        action="store_true",
        help="Invoke both `--cache` and `--tos`.",
    )


def execute(args: Namespace) -> int:
    """Execute the `tos` subcommand."""
    validate_prefix_exists(context.target_prefix)

    console = Console()
    action: Callable = render_list
    kwargs = {}
    if args.cmd == "accept":
        action = render_accept
    elif args.cmd == "reject":
        action = render_reject
    elif args.cmd == "view":
        action = render_view
    elif args.cmd == "interactive":
        action = render_interactive
        kwargs["auto_accept_tos"] = context.plugins.auto_accept_tos
    elif args.cmd == "info":
        # refactor into `conda info` plugin (when possible)
        return render_info(console=console)
    elif args.cmd == "clean":
        # refactor into `conda clean` plugin (when possible)
        return render_clean(
            cache=args.cache,
            tos=args.tos,
            all=args.all,
            tos_root=args.tos_root,
            console=console,
        )

    return action(
        *context.channels,
        tos_root=args.tos_root,
        cache_timeout=args.cache_timeout,
        console=console,
        **kwargs,
    )


@hookimpl
def conda_subcommands() -> Iterator[CondaSubcommand]:
    """Return a list of subcommands for the plugin."""
    yield CondaSubcommand(
        name="tos",
        action=execute,
        summary=(
            "A subcommand for viewing, accepting, rejecting, and otherwise interacting "
            "with a channel's Terms of Service (ToS). This plugin periodically checks "
            "for updated ToS for the active/selected channels. Channels with a ToS "
            "will need to be accepted or rejected prior to use. Conda will only allow "
            "package installation from channels without a ToS or with an accepted ToS. "
            "Attempting to use a channel with a rejected ToS will result in an error."
        ),
        configure_parser=configure_parser,
    )


@hookimpl
def conda_settings() -> Iterator[CondaSetting]:
    """Return a list of settings for the plugin."""
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
    """Return a list of pre-commands for the plugin."""
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


@cache
def _get_tos_acceptance_header() -> str:
    if CI:
        return "CI=true"

    values = []
    for channel in get_channels(*context.channels):
        try:
            local_pair = get_local_metadata(
                channel,
                extend_search_path=[DEFAULT_TOS_ROOT],
            )
        except CondaToSMissingError:
            pass
        else:
            values.append(
                KEY_SEPARATOR.join(
                    (
                        channel.base_url,
                        str(int(local_pair.metadata.version.timestamp())),
                        "accepted" if local_pair.metadata.tos_accepted else "rejected",
                        str(int(local_pair.metadata.acceptance_timestamp.timestamp())),
                    )
                )
            )
    return FIELD_SEPARATOR.join(values)


@hookimpl
def conda_request_headers(host: str, path: str) -> Iterator[CondaRequestHeader]:
    """Return a list of request headers for the plugin."""
    if (
        # only add the header to anaconda.com endpoints
        host in HOSTS
        # only add the ToS header for non-ToS endpoints
        and not path.endswith(f"/{ENDPOINT}")
    ):
        yield CondaRequestHeader(
            name="Anaconda-ToS-Accept",
            value=_get_tos_acceptance_header(),
        )
