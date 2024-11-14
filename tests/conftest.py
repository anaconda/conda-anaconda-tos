# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from conda.models.channel import Channel
from http_test_server import SAMPLE_CHANNEL_DIR, serve_channel

from anaconda_conda_tos import path
from anaconda_conda_tos.models import RemoteToSMetadata

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from pytest import MonkeyPatch, TempPathFactory

pytest_plugins = (
    # Add testing fixtures and internal pytest plugins here
    "conda.testing.fixtures",
)


@pytest.fixture
def tos_server() -> Iterator[tuple[Channel, RemoteToSMetadata]]:
    with serve_channel(
        SAMPLE_CHANNEL_DIR,
        metadata := RemoteToSMetadata(
            version=datetime.now(tz=timezone.utc),
            text=f"ToS Text\n\n{uuid4().hex}",
            support="support.com",
        ),
    ) as url:
        yield Channel(url), metadata


@pytest.fixture
def tos_channel(tos_server: tuple[Channel, RemoteToSMetadata]) -> Channel:
    return tos_server[0]


@pytest.fixture
def tos_metadata(tos_server: tuple[Channel, RemoteToSMetadata]) -> RemoteToSMetadata:
    return tos_server[1]


@pytest.fixture(scope="session")
def sample_channel() -> Iterator[Channel]:
    # Serve the sample channel as-is
    with serve_channel(SAMPLE_CHANNEL_DIR, None) as url:
        yield Channel(url)


@pytest.fixture
def mock_search_path(
    monkeypatch: MonkeyPatch,
    tmp_path_factory: TempPathFactory,
) -> tuple[Path, Path]:
    tos_root = tmp_path_factory.mktemp("tos")
    (system_tos_root := tos_root / "system").mkdir()
    (user_tos_root := tos_root / "user").mkdir()
    monkeypatch.setattr(
        path,
        "SEARCH_PATH",
        (tos_root / "other", system_tos_root, user_tos_root, "$CONDATOS"),
    )
    return (system_tos_root, user_tos_root)


@pytest.fixture(autouse=True)
def mock_cache_dir(monkeypatch: MonkeyPatch, tmp_path_factory: TempPathFactory) -> Path:
    cache_dir = tmp_path_factory.mktemp("cache")
    monkeypatch.setattr(path, "CACHE_DIR", cache_dir)
    return cache_dir
