# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import sys
from io import StringIO
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.gateways.connection.session import CondaSession, get_session

from anaconda_conda_tos.api import accept_tos, reject_tos
from anaconda_conda_tos.plugin import (
    conda_request_headers,
    conda_settings,
    conda_subcommands,
)

if TYPE_CHECKING:
    from pathlib import Path

    from conda.models.channel import Channel
    from conda.testing.fixtures import CondaCLIFixture
    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture

    from anaconda_conda_tos.models import RemoteToSMetadata


def test_subcommands_hook() -> None:
    subcommands = list(conda_subcommands())
    assert len(subcommands) == 1

    assert subcommands[0].name == "tos"

    assert "tos" in context.plugin_manager.get_subcommands()


def test_settings_hook() -> None:
    settings = list(conda_settings())
    assert len(settings) == 1

    assert settings[0].name == "auto_accept_tos"


def test_request_headers_hook() -> None:
    headers = list(conda_request_headers())
    assert len(headers) == 1

    assert headers[0].name == "Anaconda-ToS-Accept"


def test_subcommand_tos(conda_cli: CondaCLIFixture) -> None:
    out, err, code = conda_cli("tos")
    assert out
    # assert not err  # server log is output to stderr
    assert not code


def test_subcommand_tos_view(
    conda_cli: CondaCLIFixture,
    mock_channels: tuple[Channel, Channel],
    tos_full_lines: list[str],
) -> None:
    tos_channel, sample_channel = mock_channels

    out, err, code = conda_cli("tos", "view")
    assert out.splitlines() == [
        f"viewing ToS for {tos_channel}:",
        *tos_full_lines,
        f"no ToS for {sample_channel}",
    ]
    # assert not err  # server log is output to stderr
    assert not code


def test_subcommand_tos_accept(
    conda_cli: CondaCLIFixture,
    mock_channels: tuple[Channel, Channel],
    tmp_path: Path,
) -> None:
    tos_channel, sample_channel = mock_channels

    out, err, code = conda_cli("tos", "accept", f"--tos-root={tmp_path}")
    assert out.splitlines() == [
        f"accepted ToS for {tos_channel}",
        f"ToS not found for {sample_channel}",
    ]
    # assert not err  # server log is output to stderr
    assert not code


def test_subcommand_tos_reject(
    conda_cli: CondaCLIFixture,
    mock_channels: tuple[Channel, Channel],
    tmp_path: Path,
) -> None:
    tos_channel, sample_channel = mock_channels

    out, err, code = conda_cli("tos", "reject", f"--tos-root={tmp_path}")
    assert out.splitlines() == [
        f"rejected ToS for {tos_channel}",
        f"ToS not found for {sample_channel}",
    ]
    # assert not err  # server log is output to stderr
    assert not code


def test_subcommand_tos_list(
    mocker: MockerFixture,
    conda_cli: CondaCLIFixture,
    mock_channels: tuple[Channel, Channel],
    mock_search_path: tuple[Path, Path],
) -> None:
    system_tos_root, user_tos_root = mock_search_path
    tos_channel, sample_channel = mock_channels
    mocker.patch("os.get_terminal_size", return_value=os.terminal_size((200, 200)))

    out, err, code = conda_cli("tos")
    assert tos_channel.base_url in out
    assert sample_channel.base_url in out
    # assert not err  # server log is output to stderr
    assert not code

    accept_tos(tos_channel, tos_root=system_tos_root, cache_timeout=None)
    out, err, code = conda_cli("tos")
    assert tos_channel.base_url in out
    assert sample_channel.base_url in out
    # assert not err  # server log is output to stderr
    assert not code

    reject_tos(tos_channel, tos_root=user_tos_root, cache_timeout=None)
    out, err, code = conda_cli("tos")
    assert tos_channel.base_url in out
    assert sample_channel.base_url in out
    # assert not err  # server log is output to stderr
    assert not code


def test_subcommand_tos_interactive(
    monkeypatch: MonkeyPatch,
    conda_cli: CondaCLIFixture,
    tos_channel: Channel,
    sample_channel: Channel,
    mock_search_path: tuple[Path, Path],
) -> None:
    system_tos_root, user_tos_root = mock_search_path

    monkeypatch.setattr(sys, "stdin", StringIO("accept\n"))
    out, err, code = conda_cli("tos", "interactive", f"--tos-root={user_tos_root}")
    assert tos_channel.base_url in out
    assert sample_channel.base_url not in out
    # assert not err  # server log is output to stderr
    assert not code


def test_request_headers(
    tos_channel: Channel,
    mock_search_path: tuple[Path, Path],
    tos_metadata: RemoteToSMetadata,
) -> None:
    system_tos_root, user_tos_root = mock_search_path

    get_session.cache_clear()
    CondaSession.cache_clear()
    session = get_session("https://repo.anaconda.com/pkgs/main/tos.json")
    assert "Anaconda-ToS-Accept" in session.headers
    assert session.headers["Anaconda-ToS-Accept"] == ""

    accept_tos(tos_channel, tos_root=user_tos_root, cache_timeout=None)
    get_session.cache_clear()
    CondaSession.cache_clear()
    session = get_session("https://repo.anaconda.com/pkgs/main/tos.json")
    assert "Anaconda-ToS-Accept" in session.headers
    value = f"{tos_channel.base_url}={int(tos_metadata.version.timestamp())}=accepted="
    assert session.headers["Anaconda-ToS-Accept"].startswith(value)

    reject_tos(tos_channel, tos_root=user_tos_root, cache_timeout=None)
    get_session.cache_clear()
    CondaSession.cache_clear()
    session = get_session("https://repo.anaconda.com/pkgs/main/tos.json")
    assert "Anaconda-ToS-Accept" in session.headers
    value = f"{tos_channel.base_url}={int(tos_metadata.version.timestamp())}=rejected="
    assert session.headers["Anaconda-ToS-Accept"].startswith(value)
