# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from conda.base.context import context
from anaconda_conda_tos.plugin import conda_subcommands, conda_settings
from typing import TYPE_CHECKING
import pytest

if TYPE_CHECKING:
    from pytest import MonkeyPatch
    from conda.testing.fixtures import CondaCLIFixture


def test_subcommands_hook() -> None:
    subcommands = list(conda_subcommands())
    assert len(subcommands) == 1

    subcommands[0].name == "tos"

    assert "tos" in context.plugin_manager.get_subcommands()


def test_settings_hook() -> None:
    settings = list(conda_settings())
    assert len(settings) == 1

    settings[0].name == "auto_accept_tos"


def test_subcommand_tos(conda_cli: CondaCLIFixture) -> None:
    conda_cli("tos")


@pytest.mark.parametrize("flag", ["--view", "--show"])
def test_subcommand_tos_view(conda_cli: CondaCLIFixture, flag: str) -> None:
    conda_cli("tos", flag)


def test_setting_auto_accept_tos(monkeypatch: MonkeyPatch) -> None:
    assert not context.plugins.auto_accept_tos
