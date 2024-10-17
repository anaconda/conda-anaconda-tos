# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from conda.base.context import context
from conda.models.channel import Channel

from anaconda_conda_tos.exceptions import CondaToSMissingError
from anaconda_conda_tos.tos import (
    TOS_TEXT,
    get_channels,
    get_tos_endpoint,
    get_tos_text,
    view_tos,
)

if TYPE_CHECKING:
    from pytest import CaptureFixture


def test_get_tos_endpoint(tos_channel: str, sample_channel: str) -> None:
    # get ToS endpoint for ToS channel
    assert get_tos_endpoint(tos_channel, TOS_TEXT).status_code == 200

    # no ToS endpoint for sample channel
    with pytest.raises(CondaToSMissingError):
        get_tos_endpoint(sample_channel, TOS_TEXT)

    # invalid channel
    with pytest.raises(ValueError):
        get_tos_endpoint("defaults", TOS_TEXT)

    with pytest.raises(CondaToSMissingError):
        get_tos_endpoint(uuid4().hex, TOS_TEXT)

    # invalid endpoint
    with pytest.raises(ValueError):
        get_tos_endpoint(sample_channel, "invalid")  # type: ignore[arg-type]


def test_get_channels() -> None:
    defaults = set(map(Channel, context.default_channels))
    assert set(get_channels("defaults")) == defaults

    conda_forge = {Channel("conda-forge")}
    assert set(get_channels("conda-forge")) == conda_forge

    assert set(get_channels("defaults", "conda-forge")) == defaults | conda_forge


def test_get_tos_text(
    tos_channel: str,
    sample_channel: str,
    tos_full_lines: tuple[str, ...],
) -> None:
    # get full text of ToS channel
    assert get_tos_text(tos_channel).splitlines == tos_full_lines

    # no full text for sample channel
    with pytest.raises(CondaToSMissingError):
        get_tos_text(sample_channel)

    # invalid channel
    with pytest.raises(ValueError):
        get_tos_text("defaults")

    with pytest.raises(CondaToSMissingError):
        get_tos_text(uuid4().hex)


def test_view_tos(
    capsys: CaptureFixture,
    tos_channel: str,
    sample_channel: str,
    tos_full_lines: tuple[str, ...],
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
