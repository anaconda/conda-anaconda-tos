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
    from typing import Iterator

    from pytest import TempPathFactory

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
