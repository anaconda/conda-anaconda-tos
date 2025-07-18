# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import sys
from contextlib import nullcontext
from datetime import timedelta
from io import StringIO
from typing import TYPE_CHECKING

import pytest

from conda_anaconda_tos.api import accept_tos
from conda_anaconda_tos.console import render
from conda_anaconda_tos.console.render import (
    TOS_CI_ACCEPTED_TEMPLATE,
    TOS_OUTDATED,
    render_accept,
    render_info,
    render_interactive,
    render_list,
    render_reject,
    render_view,
)
from conda_anaconda_tos.exceptions import (
    CondaToSNonInteractiveError,
    CondaToSRejectedError,
)
from conda_anaconda_tos.path import SEARCH_PATH

if TYPE_CHECKING:
    from pathlib import Path

    from conda.models.channel import Channel
    from pytest import CaptureFixture, MonkeyPatch

    from conda_anaconda_tos.models import RemoteToSMetadata


def test_render_view(
    capsys: CaptureFixture,
    tos_channel: Channel,
    sample_channel: Channel,
    tos_metadata: RemoteToSMetadata,
    tmp_path: Path,
) -> None:
    render_view(tos_channel, tos_root=tmp_path, cache_timeout=None)
    out, err = capsys.readouterr()
    tos_lines = out.splitlines()
    assert tos_lines == [
        f"viewing Terms of Service for {tos_channel}:",
        *tos_metadata.text.splitlines(),
    ]
    # assert not err  # server log is output to stderr

    render_view(tos_channel, tos_root=tmp_path, cache_timeout=None, json=True)
    out, err = capsys.readouterr()
    view_json = json.loads(out)
    for tos in view_json.values():
        assert tos["text"] == tos_metadata.text
    # assert not err  # server log is output to stderr

    render_view(sample_channel, tos_root=tmp_path, cache_timeout=None)
    out, err = capsys.readouterr()
    sample_lines = out.splitlines()
    assert sample_lines == [f"no Terms of Service for {sample_channel}"]
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
    assert tos_lines == [f"accepted Terms of Service for {tos_channel}"]
    # assert not err  # server log is output to stderr

    render_accept(tos_channel, tos_root=tmp_path, cache_timeout=None, json=True)
    out, err = capsys.readouterr()
    accept_json = json.loads(out)
    for tos in accept_json.values():
        assert tos["tos_accepted"] is True
    # assert not err  # server log is output to stderr

    render_accept(sample_channel, tos_root=tmp_path, cache_timeout=None)
    out, err = capsys.readouterr()
    sample_lines = out.splitlines()
    assert sample_lines == [f"Terms of Service not found for {sample_channel}"]
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
    assert tos_lines == [f"rejected Terms of Service for {tos_channel}"]
    # assert not err  # server log is output to stderr

    render_reject(tos_channel, tos_root=tmp_path, cache_timeout=None, json=True)
    out, err = capsys.readouterr()
    reject_json = json.loads(out)
    for tos in reject_json.values():
        assert tos["tos_accepted"] is False
    # assert not err  # server log is output to stderr

    render_reject(sample_channel, tos_root=tmp_path, cache_timeout=None)
    out, err = capsys.readouterr()
    sample_lines = out.splitlines()
    assert sample_lines == [f"Terms of Service not found for {sample_channel}"]
    # assert not err  # server log is output to stderr

    render_reject(tos_channel, sample_channel, tos_root=tmp_path, cache_timeout=None)
    out, err = capsys.readouterr()
    assert out.splitlines() == [*tos_lines, *sample_lines]
    # assert not err  # server log is output to stderr


@pytest.mark.parametrize("ci", [True, False])
@pytest.mark.parametrize("verbose", [True, False])
def test_render_interactive(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
    sample_channel: Channel,
    tos_channel: Channel,
    tmp_path: Path,
    tos_metadata: RemoteToSMetadata,
    ci: bool,
    verbose: bool,
    terminal_width: int,  # noqa: ARG001
) -> None:
    monkeypatch.setattr(render, "CI", ci)
    monkeypatch.setattr(render, "IS_INTERACTIVE", True)

    render_interactive(
        sample_channel,
        tos_root=tmp_path,
        cache_timeout=None,
        auto_accept_tos=False,
        always_yes=False,
        verbose=verbose,
    )
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        *(["Gathering channels..."] if verbose else []),
        *(["Reviewing channels..."] if verbose else []),
        *(["CI detected..."] if ci else []),
        *(["0 channel Terms of Service accepted"] if verbose else []),
    ]

    with nullcontext() if ci else pytest.raises(CondaToSNonInteractiveError):
        render_interactive(
            tos_channel,
            tos_root=tmp_path / "always_yes",
            cache_timeout=None,
            auto_accept_tos=False,
            always_yes=True,
            verbose=verbose,
        )
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        *(["Gathering channels..."] if verbose else []),
        *(["Reviewing channels..."] if verbose else []),
        *(
            [
                "CI detected...",
                *TOS_CI_ACCEPTED_TEMPLATE.format(
                    channel=tos_channel,
                    tos_text=tos_metadata.text,
                ).splitlines(),
                "1 channel Terms of Service accepted",
            ]
            if ci
            else []
        ),
    ]

    monkeypatch.setattr(sys, "stdin", StringIO("accept\n"))
    render_interactive(
        tos_channel,
        tos_root=tmp_path / "accepted",
        cache_timeout=None,
        auto_accept_tos=False,
        always_yes=False,
        verbose=verbose,
    )
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        *(["Gathering channels..."] if verbose else []),
        *(["Reviewing channels..."] if verbose else []),
        *(
            [
                "CI detected...",
                *TOS_CI_ACCEPTED_TEMPLATE.format(
                    channel=tos_channel,
                    tos_text=tos_metadata.text,
                ).splitlines(),
                "1 channel Terms of Service accepted",
            ]
            if ci
            else [
                (
                    f"Do you accept the Terms of Service (ToS) for {tos_channel}? "
                    "[(a)ccept/(r)eject/(v)iew]: 1 channel Terms of Service accepted"
                )
            ]
        ),
    ]
    render_interactive(
        tos_channel,
        tos_root=tmp_path / "accepted",
        cache_timeout=None,
        auto_accept_tos=False,
        always_yes=False,
        verbose=verbose,
    )
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        *(["Gathering channels..."] if verbose else []),
        *(["Reviewing channels..."] if verbose else []),
        *(["CI detected..."] if ci else []),
        "1 channel Terms of Service accepted",
    ]

    monkeypatch.setattr(sys, "stdin", StringIO("reject\n"))
    with nullcontext() if ci else pytest.raises(CondaToSRejectedError):
        render_interactive(
            tos_channel,
            tos_root=tmp_path / "rejected",
            cache_timeout=None,
            auto_accept_tos=False,
            always_yes=False,
            verbose=verbose,
        )
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        *(["Gathering channels..."] if verbose else []),
        *(["Reviewing channels..."] if verbose else []),
        *(
            [
                "CI detected...",
                *TOS_CI_ACCEPTED_TEMPLATE.format(
                    channel=tos_channel,
                    tos_text=tos_metadata.text,
                ).splitlines(),
                "1 channel Terms of Service accepted",
            ]
            if ci
            else [
                (
                    f"Do you accept the Terms of Service (ToS) for {tos_channel}? "
                    "[(a)ccept/(r)eject/(v)iew]: 1 channel Terms of Service rejected"
                )
            ]
        ),
    ]
    with nullcontext() if ci else pytest.raises(CondaToSRejectedError):
        render_interactive(
            tos_channel,
            tos_root=tmp_path / "rejected",
            cache_timeout=None,
            auto_accept_tos=False,
            always_yes=False,
            verbose=verbose,
        )
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        *(["Gathering channels..."] if verbose else []),
        *(["Reviewing channels..."] if verbose else []),
        *(
            [
                "CI detected...",
                "1 channel Terms of Service accepted",
            ]
            if ci
            else ["1 channel Terms of Service rejected"]
        ),
    ]

    monkeypatch.setattr(sys, "stdin", StringIO("view\naccept\n"))
    render_interactive(
        tos_channel,
        tos_root=tmp_path / "viewed",
        cache_timeout=None,
        auto_accept_tos=False,
        always_yes=False,
        verbose=verbose,
    )
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        *(["Gathering channels..."] if verbose else []),
        *(["Reviewing channels..."] if verbose else []),
        *(
            [
                "CI detected...",
                *TOS_CI_ACCEPTED_TEMPLATE.format(
                    channel=tos_channel,
                    tos_text=tos_metadata.text,
                ).splitlines(),
                "1 channel Terms of Service accepted",
            ]
            if ci
            else [
                *(
                    f"Do you accept the Terms of Service (ToS) for {tos_channel}? "
                    f"[(a)ccept/(r)eject/(v)iew]: {tos_metadata.text}"
                ).splitlines(),
                (
                    f"Do you accept the Terms of Service (ToS) for {tos_channel}? "
                    "[(a)ccept/(r)eject]: 1 channel Terms of Service accepted"
                ),
            ]
        ),
    ]

    tos_metadata.version += timedelta(days=1)
    monkeypatch.setattr(sys, "stdin", StringIO("accept\n"))
    render_interactive(
        tos_channel,
        tos_root=tmp_path / "viewed",
        cache_timeout=None,
        auto_accept_tos=False,
        always_yes=False,
        verbose=verbose,
    )
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        *(["Gathering channels..."] if verbose else []),
        *(["Reviewing channels..."] if verbose else []),
        *(
            [
                "CI detected...",
                *TOS_CI_ACCEPTED_TEMPLATE.format(
                    channel=tos_channel,
                    tos_text=tos_metadata.text,
                ).splitlines(),
                "1 channel Terms of Service accepted",
            ]
            if ci
            else [
                f"The Terms of Service for {tos_channel} was previously accepted. "
                "An updated Terms of Service is now available.",
                (
                    f"Do you accept the Terms of Service (ToS) for {tos_channel}? "
                    "[(a)ccept/(r)eject/(v)iew]: 1 channel Terms of Service accepted"
                ),
            ]
        ),
    ]


def test_render_info(capsys: CaptureFixture) -> None:
    render_info()
    out, err = capsys.readouterr()
    for path in SEARCH_PATH:
        assert path in out


def test_render_info_json(capsys: CaptureFixture) -> None:
    render_info(json=True)
    out, err = capsys.readouterr()
    info_json = json.loads(out)
    for path in info_json["SEARCH_PATH"]:
        assert path in out


def test_render_list(
    tos_channel: Channel,
    tos_metadata: RemoteToSMetadata,
    tmp_path: Path,
    capsys: CaptureFixture,
    terminal_width: int,  # noqa: ARG001
) -> None:
    render_list(tos_channel, tos_root=tmp_path, cache_timeout=None)
    out, err = capsys.readouterr()
    assert str(tos_channel) in out
    assert TOS_OUTDATED not in out
    # assert not err  # server log is output to stderr

    accept_tos(tos_channel, tos_root=tmp_path, cache_timeout=None)
    render_list(tos_channel, tos_root=tmp_path, cache_timeout=None)
    out, err = capsys.readouterr()
    assert str(tos_channel) in out
    assert TOS_OUTDATED not in out
    # assert not err  # server log is output to stderr

    render_list(tos_channel, tos_root=tmp_path, cache_timeout=None, json=True)
    out, err = capsys.readouterr()
    list_json = json.loads(out)
    for tos in list_json.values():
        assert "path" in tos
    # assert not err  # server log is output to stderr

    tos_metadata.version += timedelta(days=1)
    render_list(tos_channel, tos_root=tmp_path, cache_timeout=None)
    out, err = capsys.readouterr()
    assert str(tos_channel) in out
    assert TOS_OUTDATED in out
    # assert not err  # server log is output to stderr
