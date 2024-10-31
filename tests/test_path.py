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
    get_all_channel_paths,
    get_cache_path,
    get_cache_paths,
    get_channel_paths,
    get_metadata_path,
    get_path,
    get_search_path,
    get_tos_dir,
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


def test_get_path(tmp_path: Path) -> None:
    assert get_path(SYSTEM_TOS_ROOT) == Path(context.conda_prefix, "conda-meta", "tos")
    assert get_path(USER_TOS_ROOT) == Path.home() / ".conda" / "tos"
    assert get_path(tmp_path) == tmp_path


def test_get_search_path(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    mock_tos_search_path: tuple[Path, Path],
) -> None:
    monkeypatch.setenv("CONDATOS", str(tmp_path))
    assert tuple(get_search_path()) == (*mock_tos_search_path, tmp_path)


def test_get_tos_dir(tmp_path: Path, sample_channel: str) -> None:
    assert get_tos_dir(tmp_path, sample_channel) == get_path(tmp_path) / hash_channel(
        sample_channel
    )


def test_get_metadata_path(tmp_path: Path, sample_channel: str) -> None:
    assert (
        get_metadata_path(tmp_path, sample_channel, 42)
        == get_tos_dir(tmp_path, sample_channel) / "42.json"
    )


def test_get_all_channel_paths(tmp_path: Path) -> None:
    (channel1 := tmp_path / "channel1").mkdir()
    (json1 := channel1 / "1.json").touch()
    (json2 := channel1 / "2.json").touch()
    (channel2 := tmp_path / "channel2").mkdir()
    (json3 := channel2 / "1.json").touch()
    (json4 := channel2 / "2.json").touch()
    assert sorted(get_all_channel_paths(extend_search_path=[tmp_path])) == [
        json1,
        json2,
        json3,
        json4,
    ]


def test_get_channel_paths(tmp_path: Path, sample_channel: str) -> None:
    (channel1 := tmp_path / hash_channel(sample_channel)).mkdir()
    (json1 := channel1 / "1.json").touch()
    (json2 := channel1 / "2.json").touch()
    assert sorted(get_channel_paths(sample_channel, extend_search_path=[tmp_path])) == [
        json1,
        json2,
    ]


def test_get_cache_path(sample_channel: str, mock_cache_dir: Path) -> None:
    assert (
        get_cache_path(sample_channel)
        == mock_cache_dir / f"{hash_channel(sample_channel)}.cache"
    )


def test_get_cache_paths(mock_cache_dir: Path) -> None:
    assert list(get_cache_paths()) == []
    (cache1 := mock_cache_dir / "cache1.cache").touch()
    (cache2 := mock_cache_dir / "cache2.cache").touch()
    assert sorted(get_cache_paths()) == [cache1, cache2]
