# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

from conda.base.context import context
from conda.models.channel import Channel

from anaconda_conda_tos.api import get_all_metadatas
from anaconda_conda_tos.path import get_metadata_path
from anaconda_conda_tos.tos import accept_tos, get_channels, reject_tos, view_tos

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import CaptureFixture


def test_get_channels() -> None:
    defaults = set(map(Channel, context.default_channels))
    assert set(get_channels("defaults")) == defaults

    conda_forge = {Channel("conda-forge")}
    assert set(get_channels("conda-forge")) == conda_forge

    assert set(get_channels("defaults", "conda-forge")) == defaults | conda_forge


def test_view_tos(
    capsys: CaptureFixture,
    tos_channel: str,
    sample_channel: str,
    tos_full_lines: list[str],
) -> None:
    view_tos(tos_channel)
    out, err = capsys.readouterr()
    tos_lines = out.splitlines()
    assert tos_lines == [f"viewing ToS for {tos_channel}:", *tos_full_lines]
    # assert not err  # server log is output to stderr

    view_tos(sample_channel)
    out, err = capsys.readouterr()
    sample_lines = out.splitlines()
    assert sample_lines == [f"viewing ToS for {sample_channel}:", "ToS not found"]
    # assert not err  # server log is output to stderr

    view_tos(tos_channel, sample_channel)
    out, err = capsys.readouterr()
    assert out.splitlines() == [*tos_lines, *sample_lines]
    # assert not err  # server log is output to stderr


def test_accept_tos(
    capsys: CaptureFixture,
    tos_channel: str,
    sample_channel: str,
    tmp_path: Path,
) -> None:
    accept_tos(tmp_path, tos_channel)
    out, err = capsys.readouterr()
    tos_lines = out.splitlines()
    assert tos_lines == [f"accepting ToS for {tos_channel}"]
    # assert not err  # server log is output to stderr

    accept_tos(tmp_path, sample_channel)
    out, err = capsys.readouterr()
    sample_lines = out.splitlines()
    assert sample_lines == [f"ToS not found for {sample_channel}"]
    # assert not err  # server log is output to stderr

    accept_tos(tmp_path, tos_channel, sample_channel)
    out, err = capsys.readouterr()
    assert out.splitlines() == [*tos_lines, *sample_lines]
    # assert not err  # server log is output to stderr


def test_reject_tos(
    capsys: CaptureFixture,
    tos_channel: str,
    sample_channel: str,
    tmp_path: Path,
) -> None:
    reject_tos(tmp_path, tos_channel)
    out, err = capsys.readouterr()
    tos_lines = out.splitlines()
    assert tos_lines == [f"rejecting ToS for {tos_channel}"]
    # assert not err  # server log is output to stderr

    reject_tos(tmp_path, sample_channel)
    out, err = capsys.readouterr()
    sample_lines = out.splitlines()
    assert sample_lines == [f"ToS not found for {sample_channel}"]
    # assert not err  # server log is output to stderr

    reject_tos(tmp_path, tos_channel, sample_channel)
    out, err = capsys.readouterr()
    assert out.splitlines() == [*tos_lines, *sample_lines]
    # assert not err  # server log is output to stderr


def test_get_tos(
    tos_channel: str, sample_channel: str, mock_tos_search_path: tuple[Path, Path]
) -> None:
    _, user_tos_root = mock_tos_search_path

    # list all channels and whether their ToS has been accepted
    tos = list(get_all_metadatas(tos_channel, sample_channel))
    assert len(tos) == 2
    (channel1, metadata_pair1), (channel2, metadata_pair2) = tos
    assert channel1 == Channel(tos_channel)
    assert not metadata_pair1
    assert channel2 == Channel(sample_channel)
    assert not metadata_pair2

    # accept the ToS for a channel
    accept_tos(user_tos_root, tos_channel)
    tos = list(get_all_metadatas(tos_channel, sample_channel))
    assert len(tos) == 2
    (channel1, metadata_pair1), (channel2, metadata_pair2) = tos
    assert channel1 == Channel(tos_channel)
    assert metadata_pair1
    assert metadata_pair1.metadata.tos_accepted
    assert metadata_pair1.path == get_metadata_path(user_tos_root, tos_channel, 1)
    assert channel2 == Channel(sample_channel)
    assert not metadata_pair2

    # list all channels that have been accepted even if it is not active
    accept_tos(user_tos_root, tos_channel)
    tos = list(get_all_metadatas())
    assert len(tos) == 1
    channel1, metadata_pair1 = tos[0]
    assert channel1 == Channel(tos_channel)
    assert metadata_pair1
    assert metadata_pair1.metadata.tos_accepted
    assert metadata_pair1.path == get_metadata_path(user_tos_root, tos_channel, 1)

    # even rejected ToS channels are listed
    reject_tos(user_tos_root, tos_channel)
    tos = list(get_all_metadatas())
    assert len(tos) == 1
    channel1, metadata_pair1 = tos[0]
    assert channel1 == Channel(tos_channel)
    assert metadata_pair1
    assert not metadata_pair1.metadata.tos_accepted
    assert metadata_pair1.path == get_metadata_path(user_tos_root, tos_channel, 1)
