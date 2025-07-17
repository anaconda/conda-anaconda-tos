# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from conda.auxlib.type_coercion import BOOLISH_FALSE, BOOLISH_TRUE
from conda.base.context import context
from conda.models.channel import Channel

from conda_anaconda_tos.api import _is_ci, get_channels, get_one_tos, get_stored_tos
from conda_anaconda_tos.exceptions import CondaToSMissingError
from conda_anaconda_tos.models import (
    LocalPair,
    LocalToSMetadata,
    RemotePair,
    RemoteToSMetadata,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture


def test_get_channels() -> None:
    defaults = set(map(Channel, context.default_channels))
    assert set(get_channels("defaults")) == defaults

    conda_forge = {Channel("conda-forge")}
    assert set(get_channels("conda-forge")) == conda_forge

    assert set(get_channels("defaults", "conda-forge")) == defaults | conda_forge


@pytest.fixture(scope="session")
def remote_metadata_pair() -> RemotePair:
    return RemotePair(
        metadata=RemoteToSMetadata(
            version=datetime(2024, 11, 1, tzinfo=timezone.utc),
            text="new Terms of Service",
            support="support.com",
        ),
    )


@pytest.fixture(scope="session")
def local_metadata_pair(
    remote_metadata_pair: RemotePair,
    sample_channel: Channel,
) -> LocalPair:
    return LocalPair(
        metadata=LocalToSMetadata(
            **remote_metadata_pair.metadata.model_dump(),
            base_url=sample_channel.base_url,
            tos_accepted=True,
            acceptance_timestamp=datetime.now(tz=timezone.utc),
        ),
        path=uuid4().hex,
    )


@pytest.fixture(scope="session")
def old_metadata_pair(
    sample_channel: Channel,
    remote_metadata_pair: RemotePair,
) -> LocalPair:
    return LocalPair(
        metadata=LocalToSMetadata(
            version=datetime(2024, 10, 1, tzinfo=timezone.utc),
            text="old Terms of Service",
            support="support.com",
            base_url=sample_channel.base_url,
            tos_accepted=True,
            acceptance_timestamp=datetime.now(tz=timezone.utc),
        ),
        path=uuid4().hex,
        remote=remote_metadata_pair.metadata,
    )


def test_get_one_tos(
    mocker: MockerFixture,
    tmp_path: Path,
    sample_channel: Channel,
    remote_metadata_pair: RemotePair,
    local_metadata_pair: LocalPair,
    old_metadata_pair: LocalPair,
) -> None:
    # mock remote metadata and no local metadata
    mocker.patch(
        "conda_anaconda_tos.api.get_remote_metadata",
        return_value=remote_metadata_pair.metadata,
    )
    mocker.patch(
        "conda_anaconda_tos.api.get_local_metadata",
        side_effect=CondaToSMissingError(sample_channel),
    )
    assert remote_metadata_pair == get_one_tos(
        sample_channel,
        tos_root=tmp_path,
        cache_timeout=None,
    )

    # mock local metadata version matches remote metadata version
    mocker.patch(
        "conda_anaconda_tos.api.get_local_metadata",
        return_value=local_metadata_pair,
    )
    assert local_metadata_pair == get_one_tos(
        sample_channel,
        tos_root=tmp_path,
        cache_timeout=None,
    )

    # mock local metadata version is outdated
    mocker.patch(
        "conda_anaconda_tos.api.get_local_metadata",
        return_value=old_metadata_pair,
    )
    assert old_metadata_pair == get_one_tos(
        sample_channel,
        tos_root=tmp_path,
        cache_timeout=None,
    )

    # mock local metadata exists but remote metadata are missing
    mocker.patch(
        "conda_anaconda_tos.api.get_remote_metadata",
        side_effect=CondaToSMissingError(sample_channel),
    )
    assert old_metadata_pair == get_one_tos(
        sample_channel,
        tos_root=tmp_path,
        cache_timeout=None,
    )


def test_get_stored_tos(
    mocker: MockerFixture,
    tmp_path: Path,
    sample_channel: Channel,
    remote_metadata_pair: RemotePair,
    local_metadata_pair: LocalPair,
    old_metadata_pair: LocalPair,
) -> None:
    # mock no remote metadata
    mocker.patch(
        "conda_anaconda_tos.api.get_local_metadatas",
        return_value=[(sample_channel, local_metadata_pair)],
    )
    mocker.patch(
        "conda_anaconda_tos.api.get_remote_metadata",
        side_effect=CondaToSMissingError(sample_channel),
    )
    assert not list(get_stored_tos(tos_root=tmp_path, cache_timeout=None))

    # mock local metadata version matches remote metadata version
    mocker.patch(
        "conda_anaconda_tos.api.get_remote_metadata",
        return_value=remote_metadata_pair.metadata,
    )
    metadata_pairs = list(get_stored_tos(tos_root=tmp_path, cache_timeout=None))
    assert metadata_pairs == [(sample_channel, local_metadata_pair)]

    # mock local metadata version is outdated
    mocker.patch(
        "conda_anaconda_tos.api.get_local_metadatas",
        return_value=[(sample_channel, old_metadata_pair)],
    )
    metadata_pairs = list(get_stored_tos(tos_root=tmp_path, cache_timeout=None))
    assert metadata_pairs == [(sample_channel, old_metadata_pair)]


def test_ci_detection_with_various_values(monkeypatch: MonkeyPatch) -> None:
    """Test CI detection with various truthy environment variable values."""
    # Clear all CI-related environment variables first
    env_vars_to_clear = [
        "CI",
        "TF_BUILD",
        "TEAMCITY_VERSION",
        "BAMBOO_BUILDKEY",
        "CODEBUILD_BUILD_ID",
    ]
    for var in env_vars_to_clear:
        monkeypatch.delenv(var, raising=False)

    # truthy values
    for envvar in ("CI", "TF_BUILD"):
        for truthy_value in (*BOOLISH_TRUE, "1"):
            monkeypatch.setenv(envvar, truthy_value)
            assert _is_ci(), (
                f"CI should be detected as True for {envvar}={truthy_value}"
            )
        monkeypatch.delenv(envvar)

    # flasy values
    for envvar in ("CI", "TF_BUILD"):
        for falsy_value in (*BOOLISH_FALSE, "0"):
            monkeypatch.setenv(envvar, falsy_value)
            assert not _is_ci(), (
                f"CI should be detected as False for {envvar}={falsy_value}"
            )
        monkeypatch.delenv(envvar)

    # defined values
    for envvar, value in (
        ("TEAMCITY_VERSION", "2025.03.3"),
        ("BAMBOO_BUILDKEY", "DEMO-MAIN-JOB"),
        ("CODEBUILD_BUILD_ID", "demo:b1e666..."),
    ):
        monkeypatch.setenv(envvar, value)
        assert _is_ci(), f"CI should be detected as True for {envvar}={value}"
        monkeypatch.delenv(envvar)
