# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from http_test_server import (
    TOS_FULL_TEXT,
    TOS_METADATA,
    serve_sample_channel,
    serve_tos_channel,
)

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Iterator

    from pytest import TempPathFactory
    from pytest_mock import MockerFixture

    from anaconda_conda_tos.remote import RemoteToSMetadata

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
    return TOS_FULL_TEXT.splitlines()


@pytest.fixture(scope="session")
def tos_metadata() -> RemoteToSMetadata:
    return TOS_METADATA


@pytest.fixture
def mock_get_tos_root(mocker: MockerFixture, tmp_path: Path) -> Path:
    mocker.patch("anaconda_conda_tos.path.get_tos_root", return_value=tmp_path)
    return tmp_path
