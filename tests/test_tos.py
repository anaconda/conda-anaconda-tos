# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from conda.base.context import context
from conda.models.channel import Channel

from anaconda_conda_tos.tos import (
    accept_tos,
    get_channels,
    get_tos,
    reject_tos,
    view_tos,
)

if TYPE_CHECKING:
    from pytest import CaptureFixture

pytestmark = pytest.mark.usefixtures("mock_get_tos_root")


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
) -> None:
    accept_tos(tos_channel)
    out, err = capsys.readouterr()
    tos_lines = out.splitlines()
    assert tos_lines == [f"accepting ToS for {tos_channel}"]
    # assert not err  # server log is output to stderr

    accept_tos(sample_channel)
    out, err = capsys.readouterr()
    sample_lines = out.splitlines()
    assert sample_lines == [f"ToS not found for {sample_channel}"]
    # assert not err  # server log is output to stderr

    accept_tos(tos_channel, sample_channel)
    out, err = capsys.readouterr()
    assert out.splitlines() == [*tos_lines, *sample_lines]
    # assert not err  # server log is output to stderr


def test_reject_tos(
    capsys: CaptureFixture,
    tos_channel: str,
    sample_channel: str,
) -> None:
    reject_tos(tos_channel)
    out, err = capsys.readouterr()
    tos_lines = out.splitlines()
    assert tos_lines == [f"rejecting ToS for {tos_channel}"]
    # assert not err  # server log is output to stderr

    reject_tos(sample_channel)
    out, err = capsys.readouterr()
    sample_lines = out.splitlines()
    assert sample_lines == [f"ToS not found for {sample_channel}"]
    # assert not err  # server log is output to stderr

    reject_tos(tos_channel, sample_channel)
    out, err = capsys.readouterr()
    assert out.splitlines() == [*tos_lines, *sample_lines]
    # assert not err  # server log is output to stderr


def test_get_tos(tos_channel: str, sample_channel: str) -> None:
    # list all channels and whether their ToS has been accepted
    tos = list(get_tos(tos_channel, sample_channel))
    assert len(tos) == 2
    (first_channel, first_metadata), (second_channel, second_metadata) = tos
    assert first_channel == Channel(tos_channel)
    assert not first_metadata
    assert second_channel == Channel(sample_channel)
    assert not second_metadata

    # accept the ToS for a channel
    accept_tos(tos_channel)
    tos = list(get_tos(tos_channel, sample_channel))
    assert len(tos) == 2
    (first_channel, first_metadata), (second_channel, second_metadata) = tos
    assert first_channel == Channel(tos_channel)
    assert first_metadata
    assert first_metadata.tos_accepted
    assert second_channel == Channel(sample_channel)
    assert not second_metadata

    # list all channels that have been accepted even if it is not active
    accept_tos(tos_channel)
    tos = list(get_tos())
    assert len(tos) == 1
    first_channel, first_metadata = tos[0]
    assert first_channel == Channel(tos_channel)
    assert first_metadata
    assert first_metadata.tos_accepted

    # even rejected ToS channels are listed
    reject_tos(tos_channel)
    tos = list(get_tos())
    assert len(tos) == 1
    first_channel, first_metadata = tos[0]
    assert first_channel == Channel(tos_channel)
    assert first_metadata
    assert not first_metadata.tos_accepted
