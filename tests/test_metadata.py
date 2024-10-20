# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from conda.models.channel import Channel
from pydantic import ValidationError

from anaconda_conda_tos.metadata import (
    ToSMetadata,
    get_all_tos_metadatas,
    get_channel_tos_metadata,
    read_metadata,
    write_metadata,
)
from anaconda_conda_tos.path import get_tos_path
from anaconda_conda_tos.remote import RemoteToSMetadata
from anaconda_conda_tos.tos import accept_tos, reject_tos

if TYPE_CHECKING:
    from pathlib import Path


def test_write_metadata(tos_channel: str, tmp_path: Path) -> None:
    channel = Channel(tos_channel)
    now = datetime.now(tz=timezone.utc).timestamp()
    remote = RemoteToSMetadata(tos_version=42, **{uuid4().hex: uuid4().hex})
    metadata = ToSMetadata(
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

    with pytest.raises(ValidationError):
        write_metadata(tmp_path, tos_channel, remote)

    write_metadata(tmp_path, tos_channel, remote, tos_accepted=True)

    write_metadata(tmp_path, tos_channel, metadata)
    contents = get_tos_path(tmp_path, tos_channel, 42).read_text()
    local = ToSMetadata.model_validate_json(contents)
    assert local.model_fields == metadata.model_fields
    assert all(
        getattr(local, key) == getattr(metadata, key)
        for key in set(local.model_fields) - {"acceptance_timestamp"}
    )


def test_read_metadata(
    mock_tos_search_path: tuple[Path, Path], tos_channel: str
) -> None:
    system_tos_root, user_tos_root = mock_tos_search_path
    assert not read_metadata(get_tos_path(system_tos_root, tos_channel, 1))
    accept_tos(system_tos_root, tos_channel)
    assert read_metadata(get_tos_path(system_tos_root, tos_channel, 1))


def test_get_channel_tos_metadata(
    mock_tos_search_path: tuple[Path, Path],
    tos_channel: str,
) -> None:
    system_tos_root, user_tos_root = mock_tos_search_path
    assert get_channel_tos_metadata(tos_channel) == (None, None)
    accept_tos(system_tos_root, tos_channel)
    assert len(get_channel_tos_metadata(tos_channel))
    reject_tos(user_tos_root, tos_channel)
    assert len(get_channel_tos_metadata(tos_channel))


def test_get_all_tos_metadatas(
    mock_tos_search_path: tuple[Path, Path],
    tos_channel: str,
) -> None:
    system_tos_root, user_tos_root = mock_tos_search_path
    assert len(list(get_all_tos_metadatas())) == 0
    assert len(list(get_all_tos_metadatas(tos_channel))) == 0
    accept_tos(system_tos_root, tos_channel)
    assert len(list(get_all_tos_metadatas())) == 1
    reject_tos(user_tos_root, tos_channel)
    assert len(list(get_all_tos_metadatas())) == 1
