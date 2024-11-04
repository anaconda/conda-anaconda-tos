# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from conda.base.context import context
from conda.models.channel import Channel

from anaconda_conda_tos.api import (
    get_single_metadata,
    get_stored_metadatas,
)
from anaconda_conda_tos.exceptions import CondaToSMissingError
from anaconda_conda_tos.models import (
    LocalToSMetadata,
    MetadataPathPair,
    RemoteToSMetadata,
)
from anaconda_conda_tos.tos import get_channels

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


def test_get_channels() -> None:
    defaults = set(map(Channel, context.default_channels))
    assert set(get_channels("defaults")) == defaults

    conda_forge = {Channel("conda-forge")}
    assert set(get_channels("conda-forge")) == conda_forge

    assert set(get_channels("defaults", "conda-forge")) == defaults | conda_forge


@pytest.fixture(scope="session")
def remote_metadata_pair() -> MetadataPathPair:
    return MetadataPathPair(
        metadata=RemoteToSMetadata(
            tos_version=2,
            text="new ToS",
        ),
    )


@pytest.fixture(scope="session")
def local_metadata_pair(
    remote_metadata_pair: MetadataPathPair,
    sample_channel: Channel,
) -> MetadataPathPair:
    return MetadataPathPair(
        metadata=LocalToSMetadata(
            **remote_metadata_pair.metadata.model_dump(),
            base_url=sample_channel.base_url,
            tos_accepted=True,
            acceptance_timestamp=datetime.now(),  # noqa: DTZ005
        ),
        path=uuid4().hex,
    )


@pytest.fixture(scope="session")
def old_metadata_pair(sample_channel: Channel) -> MetadataPathPair:
    return MetadataPathPair(
        metadata=LocalToSMetadata(
            tos_version=1,
            text="old ToS",
            base_url=sample_channel.base_url,
            tos_accepted=True,
            acceptance_timestamp=datetime.now(),  # noqa: DTZ005
        ),
        path=uuid4().hex,
    )


def test_get_single_metadata(
    mocker: MockerFixture,
    tmp_path: Path,
    sample_channel: Channel,
    remote_metadata_pair: MetadataPathPair,
    local_metadata_pair: MetadataPathPair,
    old_metadata_pair: MetadataPathPair,
) -> None:
    # mock remote ToS and no local ToS
    mocker.patch(
        "anaconda_conda_tos.api.get_remote_metadata",
        return_value=remote_metadata_pair.metadata,
    )
    mocker.patch(
        "anaconda_conda_tos.api.get_local_metadata",
        side_effect=CondaToSMissingError(sample_channel),
    )
    metadata_pair = get_single_metadata(sample_channel, tmp_path, cache_timeout=None)
    assert metadata_pair == remote_metadata_pair

    # mock local ToS version matches remote ToS version
    mocker.patch(
        "anaconda_conda_tos.api.get_local_metadata",
        return_value=local_metadata_pair,
    )
    metadata_pair = get_single_metadata(sample_channel, tmp_path, cache_timeout=None)
    assert metadata_pair == local_metadata_pair

    # mock local ToS version is outdated
    mocker.patch(
        "anaconda_conda_tos.api.get_local_metadata",
        return_value=old_metadata_pair,
    )
    metadata_pair = get_single_metadata(sample_channel, tmp_path, cache_timeout=None)
    assert metadata_pair == remote_metadata_pair


def test_get_stored_metadatas(
    mocker: MockerFixture,
    tmp_path: Path,
    sample_channel: Channel,
    remote_metadata_pair: MetadataPathPair,
    local_metadata_pair: MetadataPathPair,
    old_metadata_pair: MetadataPathPair,
) -> None:
    # mock no remote ToS
    mocker.patch(
        "anaconda_conda_tos.api.get_local_metadatas",
        return_value=[(sample_channel, local_metadata_pair)],
    )
    mocker.patch(
        "anaconda_conda_tos.api.get_remote_metadata",
        side_effect=CondaToSMissingError(sample_channel),
    )
    assert not list(get_stored_metadatas(tmp_path, cache_timeout=None))

    # mock local ToS version matches remote ToS version
    mocker.patch(
        "anaconda_conda_tos.api.get_remote_metadata",
        return_value=remote_metadata_pair.metadata,
    )
    metadata_pairs = list(get_stored_metadatas(tmp_path, cache_timeout=None))
    assert metadata_pairs == [(sample_channel, local_metadata_pair)]

    # mock local ToS version is outdated
    mocker.patch(
        "anaconda_conda_tos.api.get_local_metadatas",
        return_value=[(sample_channel, old_metadata_pair)],
    )
    metadata_pairs = list(get_stored_metadatas(tmp_path, cache_timeout=None))
    assert metadata_pairs == [(sample_channel, remote_metadata_pair)]
