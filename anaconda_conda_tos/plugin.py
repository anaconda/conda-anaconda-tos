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

from .console import render_accept, render_list, render_reject, render_view
from .path import ENV_TOS_ROOT, SITE_TOS_ROOT, SYSTEM_TOS_ROOT, USER_TOS_ROOT

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace
    from typing import Iterator


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
    parser.set_defaults(tos_root=USER_TOS_ROOT)

    action_grp = parser.add_argument_group("Actions")
    action = action_grp.add_mutually_exclusive_group()
    action.add_argument("--accept", "--agree", action="store_true")
    action.add_argument("--reject", "--disagree", "--withdraw", action="store_true")
    action.add_argument("--view", "--show", action="store_true")

    parser.add_argument(
        "--cache-timeout",
        action="store",
        type=int,
        default=24 * 60 * 60,
    )
    parser.add_argument(
        "--ignore-cache",
        dest="cache_timeout",
        action="store_const",
        const=0,
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
    action(
        *context.channels,
        tos_root=args.tos_root,
        cache_timeout=args.cache_timeout,
        console=Console(),
    )
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
