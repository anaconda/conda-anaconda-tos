# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

from conda.base.context import context

from anaconda_conda_tos.plugin import conda_settings, conda_subcommands

if TYPE_CHECKING:
    from conda.testing.fixtures import CondaCLIFixture
    from pytest_mock import MockerFixture


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


def test_subcommand_tos_view(
    mocker: MockerFixture,
    conda_cli: CondaCLIFixture,
    tos_channel: str,
    sample_channel: str,
    tos_full_lines: list[str],
) -> None:
    out, err, code = conda_cli(
        "tos",
        "--view",
        "--override-channels",
        f"--channel={sample_channel}",
    )
    sample_lines = out.splitlines()
    assert sample_lines == [f"viewing ToS for {sample_channel}:", "ToS not found"]
    # assert not err  # server log is output to stderr
    assert not code

    out, err, code = conda_cli(
        "tos",
        "--view",
        "--override-channels",
        f"--channel={tos_channel}",
    )
    tos_lines = out.splitlines()
    assert tos_lines == [f"viewing ToS for {tos_channel}:", *tos_full_lines]
    # assert not err  # server log is output to stderr
    assert not code

    mocker.patch(
        "conda.base.context.Context.channels",
        new_callable=mocker.PropertyMock,
        return_value=(tos_channel,),
    )
    out, err, code = conda_cli("tos", "--view")
    assert out.splitlines() == tos_lines
    # assert not err  # server log is output to stderr
    assert not code


def test_subcommand_tos_accept(
    mocker: MockerFixture,
    conda_cli: CondaCLIFixture,
    tos_channel: str,
    sample_channel: str,
) -> None:
    out, err, code = conda_cli(
        "tos",
        "--accept",
        "--override-channels",
        f"--channel={sample_channel}",
    )
    assert out.splitlines() == [f"ToS not found for {sample_channel}"]
    # assert not err  # server log is output to stderr
    assert not code

    out, err, code = conda_cli(
        "tos",
        "--accept",
        "--override-channels",
        f"--channel={tos_channel}",
    )
    assert out.splitlines() == [f"accepting ToS for {tos_channel}"]
    # assert not err  # server log is output to stderr
    assert not code

    mocker.patch(
        "conda.base.context.Context.channels",
        new_callable=mocker.PropertyMock,
        return_value=(tos_channel,),
    )
    out, err, code = conda_cli("tos", "--accept")
    assert out.splitlines() == [f"accepting ToS for {tos_channel}"]
    # assert not err  # server log is output to stderr
    assert not code


def test_setting_auto_accept_tos() -> None:
    assert not context.plugins.auto_accept_tos
