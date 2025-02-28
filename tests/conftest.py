# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from conda.models.channel import Channel
from http_test_server import SAMPLE_CHANNEL_DIR, generate_metadata, serve_channel

from conda_anaconda_tos import api, path, plugin
from conda_anaconda_tos.console import render

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from http_test_server import MetadataType
    from pytest import FixtureRequest, MonkeyPatch, TempPathFactory
    from pytest_mock import MockerFixture

    from conda_anaconda_tos.models import RemoteToSMetadata

pytest_plugins = (
    # Add testing fixtures and internal pytest plugins here
    "conda.testing.fixtures",
)


@pytest.fixture(scope="session")
def tos_server() -> Iterator[tuple[Channel, RemoteToSMetadata]]:
    """Serve the sample channel but with a `tos.json` endpoint.

    Also returning a mutable RemoteToSMetadata so tests can modify the endpoint to mock
    Terms of Service updates.
    """
    with serve_channel(SAMPLE_CHANNEL_DIR, metadata := generate_metadata()) as url:
        yield Channel(url), metadata


@pytest.fixture(scope="session")
def tos_channel(tos_server: tuple[Channel, RemoteToSMetadata]) -> Channel:
    """The channel URL for the Terms of Service server, see `tos_server` fixture."""
    return tos_server[0]


@pytest.fixture(scope="session")
def tos_metadata(tos_server: tuple[Channel, RemoteToSMetadata]) -> RemoteToSMetadata:
    """The metadata for the Terms of Service server, see `tos_server` fixture."""
    return tos_server[1]


@pytest.fixture(scope="session")
def sample_channel() -> Iterator[Channel]:
    """Serve the sample channel as-is without a `tos.json` endpoint."""
    with serve_channel(SAMPLE_CHANNEL_DIR, None) as url:
        yield Channel(url)


@pytest.fixture
def mutable_server() -> Iterator[tuple[Channel, list[MetadataType]]]:
    metadatas: list[MetadataType] = []
    with serve_channel(SAMPLE_CHANNEL_DIR, iter(metadatas)) as url:
        yield Channel(url), metadatas


@pytest.fixture
def mutable_channel(mutable_server: tuple[Channel, list[MetadataType]]) -> Channel:
    return mutable_server[0]


@pytest.fixture
def mutable_metadatas(
    mutable_server: tuple[Channel, list[MetadataType]],
) -> list[MetadataType]:
    return mutable_server[1]


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


@pytest.fixture
def terminal_width(mocker: MockerFixture, request: FixtureRequest) -> int:
    """Mock the terminal width for console output.

    If the default width is not sufficient, use an `indirect=True` parameterization with
    the desired width.
    """
    width = getattr(request, "param", 500)
    mocker.patch("os.get_terminal_size", return_value=os.terminal_size((width, 200)))
    return width


@pytest.fixture(autouse=True)
def unset_CI(monkeypatch: MonkeyPatch) -> None:  # noqa: N802
    # TODO: refactor CI constant for better test mocking
    monkeypatch.setattr(api, "CI", False)
    monkeypatch.setattr(render, "CI", False)
    monkeypatch.setattr(plugin, "CI", False)
