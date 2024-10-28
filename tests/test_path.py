# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from conda.base.context import context

from anaconda_conda_tos.path import (
    SYSTEM_TOS_ROOT,
    USER_TOS_ROOT,
    get_tos_dir,
    get_tos_path,
    get_tos_root,
    get_tos_search_path,
    hash_channel,
)

if TYPE_CHECKING:
    from pytest import MonkeyPatch


def test_hash_channel(sample_channel: str, tos_channel: str) -> None:
    assert hash_channel(sample_channel) == hash_channel(sample_channel)
    assert hash_channel(sample_channel) != hash_channel(tos_channel)

    # invalid channel
    with pytest.raises(ValueError):
        hash_channel("defaults")


def test_get_tos_root(tmp_path: Path) -> None:
    assert get_tos_root(SYSTEM_TOS_ROOT) == Path(
        context.conda_prefix, "conda-meta", "tos"
    )
    assert get_tos_root(USER_TOS_ROOT) == Path.home() / ".conda" / "tos"
    assert get_tos_root(tmp_path) == tmp_path


def test_get_tos_search_path(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    mock_tos_search_path: tuple[Path, Path],
) -> None:
    monkeypatch.setenv("CONDATOS", str(tmp_path))
    assert tuple(get_tos_search_path()) == (*mock_tos_search_path, tmp_path)


def test_get_tos_dir(tmp_path: Path, sample_channel: str) -> None:
    assert get_tos_dir(tmp_path, sample_channel) == get_tos_root(
        tmp_path
    ) / hash_channel(sample_channel)


def test_get_tos_path(tmp_path: Path, sample_channel: str) -> None:
    assert (
        get_tos_path(tmp_path, sample_channel, 42)
        == get_tos_dir(tmp_path, sample_channel) / "42.json"
    )
