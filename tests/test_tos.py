# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

from anaconda_conda_tos.tos import accept_tos, reject_tos, view_tos

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import CaptureFixture


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
