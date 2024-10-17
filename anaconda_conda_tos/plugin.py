# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS subcommand and settings plugins."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.common.configuration import PrimitiveParameter
from conda.plugins import CondaSetting, CondaSubcommand, hookimpl

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace
    from typing import Iterator


def configure_parser(parser: ArgumentParser) -> None:
    """Configure the parser for the `tos` subcommand."""
    parser = parser


def execute(args: Namespace) -> int:
    """Execute the `tos` subcommand."""
    args = args
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
