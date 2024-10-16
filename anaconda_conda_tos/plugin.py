# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
ToS subcommand and settings plugins.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.plugins import hookimpl, CondaSubcommand, CondaSetting
from conda.common.configuration import PrimitiveParameter

if TYPE_CHECKING:
    from argparse import Namespace, ArgumentParser


def configure_parser(parser: ArgumentParser):
    pass


def execute(args: Namespace) -> int:
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
