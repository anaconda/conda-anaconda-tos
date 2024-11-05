# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from conda.base.context import context
from conda.common.compat import on_win

from anaconda_conda_tos.path import (
    ENV_TOS_ROOT,
    SITE_TOS_ROOT,
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
    from conda.models.channel import Channel
    from pytest import MonkeyPatch


def test_hash_channel(sample_channel: Channel, tos_channel: Channel) -> None:
    assert hash_channel(sample_channel) == hash_channel(sample_channel)
    assert hash_channel(sample_channel) != hash_channel(tos_channel)

    # invalid channel
    with pytest.raises(ValueError):
        hash_channel("defaults")


def test_get_path(tmp_path: Path) -> None:
    if on_win:
        assert get_path(SITE_TOS_ROOT) == Path("C:/ProgramData/conda/tos")
    else:
        assert get_path(SITE_TOS_ROOT) == Path("/etc/conda/tos")
    assert get_path(SYSTEM_TOS_ROOT) == Path(context.conda_prefix, "conda-meta", "tos")
    assert get_path(USER_TOS_ROOT) == Path.home() / ".conda" / "tos"
    assert get_path(ENV_TOS_ROOT) == Path(context.target_prefix, "conda-meta", "tos")
    assert get_path(str(tmp_path)) == tmp_path
    assert get_path(tmp_path) == tmp_path

    # invalid path
    with pytest.raises(TypeError):
        get_path(42)  # type: ignore[arg-type]


def test_get_search_path(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    mock_search_path: tuple[Path, Path],
) -> None:
    # pass in extra paths
    assert tuple(get_search_path([tmp_path])) == (*mock_search_path, tmp_path)

    # set $CONDATOS
    monkeypatch.setenv("CONDATOS", str(tmp_path))
    assert tuple(get_search_path()) == (*mock_search_path, tmp_path)


def test_get_tos_dir(tmp_path: Path, sample_channel: Channel) -> None:
    expected = get_path(tmp_path) / hash_channel(sample_channel)
    assert get_tos_dir(tmp_path, sample_channel) == expected


def test_get_metadata_path(tmp_path: Path, sample_channel: Channel) -> None:
    expected = get_tos_dir(tmp_path, sample_channel) / "42.json"
    assert get_metadata_path(tmp_path, sample_channel, 42) == expected


def test_get_all_channel_paths(
    tmp_path: Path,
    mock_search_path: tuple[Path, Path],
) -> None:
    system_tos_root, user_tos_root = mock_search_path

    (channel1 := system_tos_root / "channel1").mkdir()
    (json1 := channel1 / "1.json").touch()

    (channel2 := user_tos_root / "channel2").mkdir()
    (json2 := channel2 / "2.json").touch()

    (channel3 := tmp_path / "channel3").mkdir()
    (json3 := channel3 / "3.json").touch()
    (channel4 := tmp_path / "channel4").mkdir()
    (json4 := channel4 / "4.json").touch()

    paths = get_all_channel_paths()
    assert list(paths) == [json1, json2]

    paths = get_all_channel_paths(extend_search_path=[tmp_path])
    assert list(paths) == [json1, json2, json3, json4]


def test_get_channel_paths(
    tmp_path: Path,
    sample_channel: Channel,
    mock_search_path: tuple[Path, Path],
) -> None:
    system_tos_root, user_tos_root = mock_search_path

    (channel1 := system_tos_root / hash_channel(sample_channel)).mkdir()
    (json1 := channel1 / "1.json").touch()

    (channel2 := user_tos_root / hash_channel(sample_channel)).mkdir()
    (json2 := channel2 / "2.json").touch()

    (channel3 := tmp_path / hash_channel(sample_channel)).mkdir()
    (json3 := channel3 / "3.json").touch()

    paths = get_channel_paths(sample_channel)
    assert list(paths) == [json1, json2]

    paths = get_channel_paths(sample_channel, extend_search_path=[tmp_path])
    assert list(paths) == [json1, json2, json3]


def test_get_cache_path(mock_cache_dir: Path, sample_channel: Channel) -> None:
    expected = mock_cache_dir / f"{hash_channel(sample_channel)}.cache"
    assert get_cache_path(sample_channel) == expected


def test_get_cache_paths(mock_cache_dir: Path) -> None:
    (cache1 := mock_cache_dir / "cache1.cache").touch()
    (cache2 := mock_cache_dir / "cache2.cache").touch()

    assert sorted(get_cache_paths()) == [cache1, cache2]
