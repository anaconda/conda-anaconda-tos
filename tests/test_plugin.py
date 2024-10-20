# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

from conda.base.context import context

from anaconda_conda_tos.plugin import conda_settings, conda_subcommands
from anaconda_conda_tos.tos import accept_tos, reject_tos

if TYPE_CHECKING:
    from pathlib import Path

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
    out, err, code = conda_cli("tos")
    assert out
    # assert not err  # server log is output to stderr
    assert not code


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
    tmp_path: Path,
) -> None:
    out, err, code = conda_cli(
        "tos",
        "--accept",
        "--override-channels",
        f"--channel={sample_channel}",
        f"--file={tmp_path}",
    )
    assert out.splitlines() == [f"ToS not found for {sample_channel}"]
    # assert not err  # server log is output to stderr
    assert not code

    out, err, code = conda_cli(
        "tos",
        "--accept",
        "--override-channels",
        f"--channel={tos_channel}",
        f"--file={tmp_path}",
    )
    assert out.splitlines() == [f"accepting ToS for {tos_channel}"]
    # assert not err  # server log is output to stderr
    assert not code

    mocker.patch(
        "conda.base.context.Context.channels",
        new_callable=mocker.PropertyMock,
        return_value=(tos_channel,),
    )
    out, err, code = conda_cli("tos", "--accept", f"--file={tmp_path}")
    assert out.splitlines() == [f"accepting ToS for {tos_channel}"]
    # assert not err  # server log is output to stderr
    assert not code


def test_subcommand_tos_reject(
    mocker: MockerFixture,
    conda_cli: CondaCLIFixture,
    tos_channel: str,
    sample_channel: str,
    tmp_path: Path,
) -> None:
    out, err, code = conda_cli(
        "tos",
        "--reject",
        "--override-channels",
        f"--channel={sample_channel}",
        f"--file={tmp_path}",
    )
    assert out.splitlines() == [f"ToS not found for {sample_channel}"]
    # assert not err  # server log is output to stderr
    assert not code

    out, err, code = conda_cli(
        "tos",
        "--reject",
        "--override-channels",
        f"--channel={tos_channel}",
        f"--file={tmp_path}",
    )
    assert out.splitlines() == [f"rejecting ToS for {tos_channel}"]
    # assert not err  # server log is output to stderr
    assert not code

    mocker.patch(
        "conda.base.context.Context.channels",
        new_callable=mocker.PropertyMock,
        return_value=(tos_channel,),
    )
    out, err, code = conda_cli("tos", "--reject", f"--file={tmp_path}")
    assert out.splitlines() == [f"rejecting ToS for {tos_channel}"]
    # assert not err  # server log is output to stderr
    assert not code


def test_subcommand_tos_list(
    mocker: MockerFixture,
    conda_cli: CondaCLIFixture,
    tos_channel: str,
    sample_channel: str,
    mock_tos_search_path: tuple[Path, Path],
) -> None:
    system_tos_root, user_tos_root = mock_tos_search_path

    out, err, code = conda_cli(
        "tos",
        "--override-channels",
        f"--channel={tos_channel}",
        f"--channel={sample_channel}",
    )
    assert tos_channel in out
    assert sample_channel in out
    # assert not err  # server log is output to stderr
    assert not code

    mocker.patch(
        "conda.base.context.Context.channels",
        new_callable=mocker.PropertyMock,
        return_value=(tos_channel, sample_channel),
    )
    out, err, code = conda_cli("tos")
    assert tos_channel in out
    assert sample_channel in out
    # assert not err  # server log is output to stderr
    assert not code

    accept_tos(system_tos_root, tos_channel)
    out, err, code = conda_cli("tos")
    assert tos_channel in out
    assert sample_channel in out
    # assert not err  # server log is output to stderr
    assert not code

    reject_tos(user_tos_root, tos_channel)
    out, err, code = conda_cli("tos")
    assert tos_channel in out
    assert sample_channel in out
    # assert not err  # server log is output to stderr
    assert not code


def test_setting_auto_accept_tos() -> None:
    assert not context.plugins.auto_accept_tos
