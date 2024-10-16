# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
ToS subcommand and settings plugins.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime

from conda.base.context import context
from conda.plugins import hookimpl, CondaSubcommand, CondaSetting
from conda.common.configuration import PrimitiveParameter
from rich.table import Table
from rich.console import Console

from .tos import view_tos, accept_tos, reject_tos, get_tos

if TYPE_CHECKING:
    from argparse import Namespace, ArgumentParser


def configure_parser(parser: ArgumentParser):
    parser.add_argument("-c", "--channel", action="append")
    parser.add_argument("--override-channels", action="store_true")

    mutex = parser.add_mutually_exclusive_group()
    mutex.add_argument("--view", "--show", action="store_true")


def execute(args: Namespace) -> int:
    if args.view:
        view_tos(*context.channels)
    return 0


@hookimpl
def conda_subcommands():
    yield CondaSubcommand(
        name="tos",
        action=execute,
        summary="View, accept, and interact with a channel's Terms of Service (ToS).",
        configure_parser=configure_parser,
    )


@hookimpl
def conda_settings():
    yield CondaSetting(
        name="auto_accept_tos",
        description="Automatically accept Terms of Service (ToS) for all channels.",
        parameter=PrimitiveParameter(False, element_type=bool),
    )
