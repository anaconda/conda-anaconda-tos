# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from conda.models.channel import Channel
from http_test_server import SAMPLE_CHANNEL_DIR, generate_metadata, serve_channel

from conda_anaconda_tos import path

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from pytest import MonkeyPatch, TempPathFactory
    from pytest_mock import MockerFixture

    from conda_anaconda_tos.models import RemoteToSMetadata

pytest_plugins = (
    # Add testing fixtures and internal pytest plugins here
    "conda.testing.fixtures",
)


@pytest.fixture
def tos_server() -> Iterator[tuple[Channel, RemoteToSMetadata]]:
    """Serve the sample channel but with a `tos.json` endpoint.

    Also returning a mutable RemoteToSMetadata so tests can modify the endpoint to mock
    ToS updates.
    """
    with serve_channel(SAMPLE_CHANNEL_DIR, metadata := generate_metadata()) as url:
        yield Channel(url), metadata


@pytest.fixture
def tos_channel(tos_server: tuple[Channel, RemoteToSMetadata]) -> Channel:
    """The channel URL for the ToS server, see `tos_server` fixture."""
    return tos_server[0]


@pytest.fixture
def tos_metadata(tos_server: tuple[Channel, RemoteToSMetadata]) -> RemoteToSMetadata:
    """The metadata for the ToS server, see `tos_server` fixture."""
    return tos_server[1]


@pytest.fixture(scope="session")
def sample_channel() -> Iterator[Channel]:
    """Serve the sample channel as-is without a `tos.json` endpoint."""
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


@pytest.fixture(autouse=True)
def mock_channels(
    mocker: MockerFixture,
    tos_channel: Channel,
    sample_channel: Channel,
) -> tuple[Channel, Channel]:
    mocker.patch(
        "conda.base.context.Context.channels",
        new_callable=mocker.PropertyMock,
        return_value=(channels := (tos_channel, sample_channel)),
    )
    return channels
