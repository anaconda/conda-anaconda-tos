# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from conda.models.channel import Channel

from anaconda_conda_tos.local import (
    get_local_metadata,
    read_metadata,
    touch_cache,
    write_metadata,
)
from anaconda_conda_tos.models import LocalToSMetadata, RemoteToSMetadata
from anaconda_conda_tos.path import get_metadata_path
from anaconda_conda_tos.tos import accept_tos, reject_tos

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


def test_touch_cache(
    mocker: MockerFixture,
    tmp_path: Path,
    sample_channel: str,
) -> None:
    path = tmp_path / "cache"
    mocker.patch("anaconda_conda_tos.local.get_cache_path", return_value=path)

    now = datetime.now().timestamp()  # noqa: DTZ005
    touch_cache(sample_channel)
    assert now < path.stat().st_mtime

    now = datetime.now().timestamp()  # noqa: DTZ005
    touch_cache(sample_channel)
    assert now < path.stat().st_mtime


def test_write_metadata(tos_channel: str, tmp_path: Path) -> None:
    channel = Channel(tos_channel)
    now = datetime.now(tz=timezone.utc).timestamp()
    remote = RemoteToSMetadata(
        tos_version=42,
        text=f"ToS full text\n\n{uuid4().hex}",
        **{uuid4().hex: uuid4().hex},
    )
    metadata = LocalToSMetadata(
        **remote.model_dump(),
        tos_accepted=True,
        # the following fields are overridden in write_metadata
        acceptance_timestamp=now,
        base_url=channel.base_url,
    )

    with pytest.raises(ValueError):
        write_metadata(tmp_path, "defaults", metadata)

    write_metadata(tmp_path, tos_channel, metadata)

    with pytest.raises(TypeError):
        write_metadata(tmp_path, tos_channel, "metadata")  # type: ignore[arg-type]

    write_metadata(tmp_path, tos_channel, remote)

    write_metadata(tmp_path, tos_channel, remote, tos_accepted=True)

    write_metadata(tmp_path, tos_channel, metadata)
    contents = get_metadata_path(tmp_path, tos_channel, 42).read_text()
    local = LocalToSMetadata.model_validate_json(contents)
    assert local.model_fields == metadata.model_fields
    assert all(
        getattr(local, key) == getattr(metadata, key)
        for key in set(local.model_fields) - {"acceptance_timestamp"}
    )


def test_read_metadata(
    mock_tos_search_path: tuple[Path, Path],
    tos_channel: str,
) -> None:
    system_tos_root, user_tos_root = mock_tos_search_path
    assert not read_metadata(get_metadata_path(system_tos_root, tos_channel, 1))
    accept_tos(system_tos_root, tos_channel, cache_timeout=0)
    assert read_metadata(get_metadata_path(system_tos_root, tos_channel, 1))


def test_get_local_metadata(
    mock_tos_search_path: tuple[Path, Path],
    tos_channel: str,
) -> None:
    system_tos_root, user_tos_root = mock_tos_search_path
    assert get_local_metadata(tos_channel) == (None, None)
    accept_tos(system_tos_root, tos_channel, cache_timeout=0)
    assert len(get_local_metadata(tos_channel))
    reject_tos(user_tos_root, tos_channel, cache_timeout=0)
    assert len(get_local_metadata(tos_channel))
