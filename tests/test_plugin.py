# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

from conda.base.context import context

from anaconda_conda_tos.plugin import conda_settings, conda_subcommands

if TYPE_CHECKING:
    from conda.testing.fixtures import CondaCLIFixture


def test_subcommands_hook() -> None:
    subcommands = list(conda_subcommands())
    assert len(subcommands) == 1

    assert subcommands[0].name == "tos"

    assert "tos" in context.plugin_manager.get_subcommands()


def test_settings_hook() -> None:
    settings = list(conda_settings())
    assert len(settings) == 1

    assert settings[0].name == "auto_accept_tos"


def test_subcommand_tos(conda_cli: CondaCLIFixture) -> None:
    conda_cli("tos")


def test_setting_auto_accept_tos() -> None:
    assert not context.plugins.auto_accept_tos
