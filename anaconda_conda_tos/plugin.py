# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS subcommand and settings plugins."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.base.context import context
from conda.cli.install import validate_prefix_exists
from conda.common.configuration import PrimitiveParameter
from conda.plugins import CondaSetting, CondaSubcommand, hookimpl

from .console import list_tos
from .path import (
    SYSTEM_TOS_ROOT,
    USER_TOS_ROOT,
)
from .tos import (
    accept_tos,
    clean_cache,
    clean_tos,
    info_tos,
    reject_tos,
    view_tos,
)

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
    action.add_argument("--info", action="store_true")
    action.add_argument("--clean-cache", action="store_true")
    action.add_argument("--clean-tos", action="store_true")

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

    if args.info:
        # TODO: refactor into `conda info` plugin
        info_tos()
    elif args.clean_cache:
        # TODO: refactor info `conda clean` plugin
        clean_cache()
    elif args.clean_tos:
        # TODO: refactor info `conda clean` plugin
        clean_tos()
    else:
        action = list_tos
        if args.accept:
            action = accept_tos
        elif args.reject:
            action = reject_tos
        elif args.view:
            action = view_tos
        action(
            *context.channels,
            tos_root=args.tos_root,
            cache_timeout=args.cache_timeout,
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
