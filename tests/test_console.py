# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

from anaconda_conda_tos.console import render_accept, render_reject, render_view

if TYPE_CHECKING:
    from pathlib import Path

    from conda.models.channel import Channel
    from pytest import CaptureFixture


def test_render_view(
    capsys: CaptureFixture,
    tos_channel: Channel,
    sample_channel: Channel,
    tos_full_lines: list[str],
    tmp_path: Path,
) -> None:
    render_view(tos_channel, tos_root=tmp_path, cache_timeout=None)
    out, err = capsys.readouterr()
    tos_lines = out.splitlines()
    assert tos_lines == [f"viewing ToS for {tos_channel}:", *tos_full_lines]
    # assert not err  # server log is output to stderr

    render_view(sample_channel, tos_root=tmp_path, cache_timeout=None)
    out, err = capsys.readouterr()
    sample_lines = out.splitlines()
    assert sample_lines == [f"no ToS for {sample_channel}"]
    # assert not err  # server log is output to stderr

    render_view(tos_channel, sample_channel, tos_root=tmp_path, cache_timeout=None)
    out, err = capsys.readouterr()
    assert out.splitlines() == [*tos_lines, *sample_lines]
    # assert not err  # server log is output to stderr


def test_render_accept(
    capsys: CaptureFixture,
    tos_channel: Channel,
    sample_channel: Channel,
    tmp_path: Path,
) -> None:
    render_accept(tos_channel, tos_root=tmp_path, cache_timeout=None)
    out, err = capsys.readouterr()
    tos_lines = out.splitlines()
    assert tos_lines == [f"accepted ToS for {tos_channel}"]
    # assert not err  # server log is output to stderr

    render_accept(sample_channel, tos_root=tmp_path, cache_timeout=None)
    out, err = capsys.readouterr()
    sample_lines = out.splitlines()
    assert sample_lines == [f"ToS not found for {sample_channel}"]
    # assert not err  # server log is output to stderr

    render_accept(tos_channel, sample_channel, tos_root=tmp_path, cache_timeout=None)
    out, err = capsys.readouterr()
    assert out.splitlines() == [*tos_lines, *sample_lines]
    # assert not err  # server log is output to stderr


def test_render_reject(
    capsys: CaptureFixture,
    tos_channel: Channel,
    sample_channel: Channel,
    tmp_path: Path,
) -> None:
    render_reject(tos_channel, tos_root=tmp_path, cache_timeout=None)
    out, err = capsys.readouterr()
    tos_lines = out.splitlines()
    assert tos_lines == [f"rejected ToS for {tos_channel}"]
    # assert not err  # server log is output to stderr

    render_reject(sample_channel, tos_root=tmp_path, cache_timeout=None)
    out, err = capsys.readouterr()
    sample_lines = out.splitlines()
    assert sample_lines == [f"ToS not found for {sample_channel}"]
    # assert not err  # server log is output to stderr

    render_reject(tos_channel, sample_channel, tos_root=tmp_path, cache_timeout=None)
    out, err = capsys.readouterr()
    assert out.splitlines() == [*tos_lines, *sample_lines]
    # assert not err  # server log is output to stderr
