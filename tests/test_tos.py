# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

from conda.base.context import context
from conda.models.channel import Channel

from anaconda_conda_tos.tos import get_channels, view_tos

if TYPE_CHECKING:
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
