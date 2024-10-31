# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from http_test_server import (
    TOS_METADATA,
    TOS_TEXT,
    serve_sample_channel,
    serve_tos_channel,
)

from anaconda_conda_tos import path

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Iterator

    from pytest import MonkeyPatch, TempPathFactory

    from anaconda_conda_tos.models import RemoteToSMetadata

pytest_plugins = (
    # Add testing fixtures and internal pytest plugins here
    "conda.testing.fixtures",
)


@pytest.fixture(scope="session")
def tos_channel(tmp_path_factory: TempPathFactory) -> Iterator[str]:
    path = tmp_path_factory.mktemp("tos_channel")
    with serve_tos_channel(path) as url:
        yield url


@pytest.fixture(scope="session")
def sample_channel() -> Iterator[str]:
    # Serve the sample channel as-is
    with serve_sample_channel() as url:
        yield url


@pytest.fixture(scope="session")
def tos_full_lines() -> list[str]:
    return TOS_TEXT.splitlines()


@pytest.fixture(scope="session")
def tos_metadata() -> RemoteToSMetadata:
    return TOS_METADATA


@pytest.fixture
def mock_tos_search_path(
    monkeypatch: MonkeyPatch,
    tmp_path_factory: TempPathFactory,
) -> tuple[Path, Path]:
    tos_root = tmp_path_factory.mktemp("tos")
    (system_tos_root := tos_root / "system").mkdir()
    (user_tos_root := tos_root / "user").mkdir()
    monkeypatch.setattr(
        path,
        "SEARCH_PATH",
        (tos_root / "unused", system_tos_root, user_tos_root, "$CONDATOS"),
    )
    return (system_tos_root, user_tos_root)


@pytest.fixture(autouse=True)
def mock_cache_dir(monkeypatch: MonkeyPatch, tmp_path_factory: TempPathFactory) -> Path:
    cache_dir = tmp_path_factory.mktemp("cache")
    monkeypatch.setattr(path, "CACHE_DIR", cache_dir)
    return cache_dir
