# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from conda.common.compat import on_win
from http_test_server import generate_metadata

from conda_anaconda_tos.exceptions import (
    CondaToSInvalidError,
    CondaToSMissingError,
    CondaToSPermissionError,
)
from conda_anaconda_tos.models import RemoteToSMetadata
from conda_anaconda_tos.path import get_cache_path
from conda_anaconda_tos.remote import (
    get_cached_endpoint,
    get_endpoint,
    get_remote_metadata,
    write_cached_endpoint,
)

if TYPE_CHECKING:
    from pathlib import Path

    from conda.models.channel import Channel
    from http_test_server import MetadataType
    from pytest_mock import MockerFixture

TIMESTAMP1 = datetime(2024, 10, 1, tzinfo=timezone.utc)  # "version 1"
REMOTE_METADATA = RemoteToSMetadata(
    version=TIMESTAMP1,
    text=f"ToS full text\n\n{uuid4().hex}",
    support="support.com",
    **{uuid4().hex: uuid4().hex},
)


def test_get_endpoint(tos_channel: Channel, sample_channel: Channel) -> None:
    # get Terms of Service endpoint for Terms of Service channel
    assert get_endpoint(tos_channel).status_code == 200

    # no Terms of Service endpoint for sample channel
    with pytest.raises(CondaToSMissingError):
        get_endpoint(sample_channel)

    # invalid channel
    with pytest.raises(ValueError):
        get_endpoint("defaults")

    with pytest.raises(CondaToSMissingError):
        get_endpoint(uuid4().hex)


def test_get_endpoint_mutable_server(
    mutable_channel: Channel, mutable_metadatas: list[MetadataType]
) -> None:
    # first no endpoint
    mutable_metadatas.append(None)
    with pytest.raises(CondaToSMissingError):
        get_endpoint(mutable_channel)

    # second valid endpoint
    mutable_metadatas.append(metadata := generate_metadata())
    response = get_endpoint(mutable_channel)
    assert response.status_code == 200
    assert RemoteToSMetadata(**response.json()) == metadata

    # finally no endpoint again
    mutable_metadatas.append(None)
    with pytest.raises(CondaToSMissingError):
        get_endpoint(mutable_channel)


def test_get_cached_endpoint(sample_channel: Channel) -> None:
    path = get_cache_path(sample_channel)
    assert not path.exists()

    # falsy cache_timeout
    assert get_cached_endpoint(sample_channel, cache_timeout=0) is None
    assert get_cached_endpoint(sample_channel, cache_timeout=0.0) is None
    assert get_cached_endpoint(sample_channel, cache_timeout=None) is None
    assert get_cached_endpoint(sample_channel, cache_timeout=False) is None

    # invalid cache_timeout
    with pytest.raises(TypeError):
        get_cached_endpoint(sample_channel, cache_timeout=object())  # type: ignore[arg-type]

    # missing file/no mtime
    assert get_cached_endpoint(sample_channel) is None

    # touch cache file in the past
    path.touch()
    os.utime(path, (path.stat().st_atime, path.stat().st_mtime - 100))

    # cache file is fresh
    assert get_cached_endpoint(sample_channel, cache_timeout=1000) == path

    # cache file is stale
    assert get_cached_endpoint(sample_channel, cache_timeout=10) is None


def test_write_cached_endpoint(
    sample_channel: Channel,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    path = get_cache_path(sample_channel)
    assert not path.exists()

    write_cached_endpoint(sample_channel, None)
    assert path.exists()
    assert not path.read_text()

    write_cached_endpoint(sample_channel, REMOTE_METADATA)
    assert path.exists()
    assert RemoteToSMetadata.model_validate_json(path.read_text()) == REMOTE_METADATA

    with pytest.raises(TypeError):
        write_cached_endpoint(sample_channel, object())  # type: ignore[arg-type]

    (path := tmp_path / "cache").touch()
    mocker.patch("conda_anaconda_tos.remote.get_cache_path", return_value=path)
    try:
        path.chmod(0o000)
        with pytest.raises(CondaToSPermissionError):
            write_cached_endpoint(sample_channel, REMOTE_METADATA)
    finally:
        # cleanup so tmp_path can be removed
        path.chmod(0o644)


def test_get_remote_metadata(
    tos_channel: Channel,
    sample_channel: Channel,
    tos_metadata: RemoteToSMetadata,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    # get metadata of Terms of Service channel
    assert get_remote_metadata(tos_channel) == tos_metadata
    assert get_remote_metadata(tos_channel, cache_timeout=100) == tos_metadata

    # no metadata for sample channel
    with pytest.raises(CondaToSMissingError):
        get_remote_metadata(sample_channel)

    # invalid channel
    with pytest.raises(ValueError):
        get_remote_metadata("defaults")

    with pytest.raises(CondaToSMissingError):
        get_remote_metadata(uuid4().hex)

    mocker.patch("conda_anaconda_tos.remote.get_endpoint", return_value=None)
    with pytest.raises(CondaToSInvalidError):
        get_remote_metadata(tos_channel)

    mocker.patch("conda_anaconda_tos.remote.get_endpoint", return_value=42)
    with pytest.raises(CondaToSInvalidError):
        get_remote_metadata(tos_channel)

    mocker.patch("conda_anaconda_tos.remote.get_endpoint", return_value={})
    with pytest.raises(CondaToSInvalidError):
        get_remote_metadata(tos_channel)

    cache = tmp_path / "cache"
    mocker.patch("conda_anaconda_tos.remote.get_cached_endpoint", return_value=cache)
    with pytest.raises(CondaToSMissingError):
        get_remote_metadata(tos_channel)

    cache.touch()
    with pytest.raises(CondaToSMissingError):
        get_remote_metadata(tos_channel)

    try:
        cache.chmod(0o000)
        with pytest.raises(CondaToSMissingError if on_win else CondaToSPermissionError):
            # Windows can only make the path read-only
            get_remote_metadata(tos_channel)
    finally:
        # cleanup so tmp_path can be removed
        cache.chmod(0o644)

    cache.write_text("{}")
    with pytest.raises(CondaToSInvalidError):
        get_remote_metadata(tos_channel)


def test_get_remote_metadata_mutable_server(
    mutable_channel: Channel,
    mutable_metadatas: list[MetadataType],
) -> None:
    # first no endpoint
    mutable_metadatas.append(None)
    with pytest.raises(CondaToSMissingError):
        get_remote_metadata(mutable_channel)

    # second non-JSON endpoint
    mutable_metadatas.append("?")
    with pytest.raises(CondaToSInvalidError):
        get_remote_metadata(mutable_channel)

    # third invalid schema endpoint
    mutable_metadatas.append("{'version': null}")
    with pytest.raises(CondaToSInvalidError):
        get_remote_metadata(mutable_channel)

    # fourth valid endpoint
    metadata = generate_metadata()
    mutable_metadatas.append(metadata)
    assert get_remote_metadata(mutable_channel) == metadata

    # finally no endpoint again
    mutable_metadatas.append(None)
    with pytest.raises(CondaToSMissingError):
        get_remote_metadata(mutable_channel)
