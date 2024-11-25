# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from conda.common.compat import on_win
from conda.models.channel import Channel
from pydantic import ValidationError

from conda_anaconda_tos.exceptions import CondaToSMissingError, CondaToSPermissionError
from conda_anaconda_tos.local import (
    get_local_metadata,
    get_local_metadatas,
    read_metadata,
    write_metadata,
)
from conda_anaconda_tos.models import LocalPair, LocalToSMetadata, RemoteToSMetadata
from conda_anaconda_tos.path import get_metadata_path

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch


CHANNEL = Channel("someplace")
TIMESTAMP1 = datetime(2024, 10, 1, tzinfo=timezone.utc)  # "version 1"
NOW = datetime.now(tz=timezone.utc)
REMOTE_METADATA = RemoteToSMetadata(
    version=TIMESTAMP1,
    text=f"Terms of Service full text\n\n{uuid4().hex}",
    support="support.com",
    **{uuid4().hex: uuid4().hex},
)
LOCAL_METADATA = LocalToSMetadata(
    **REMOTE_METADATA.model_dump(),
    tos_accepted=True,
    acceptance_timestamp=NOW,
    base_url=CHANNEL.base_url,
)


def _similar_metadata(
    metadata1: LocalToSMetadata | RemoteToSMetadata,
    metadata2: LocalToSMetadata | RemoteToSMetadata,
) -> bool:
    return type(metadata1) is type(metadata2) and all(
        getattr(metadata1, key) == getattr(metadata2, key)
        for key in set(metadata1.model_fields) - {"acceptance_timestamp"}
    )


def test_write_metadata(tmp_path: Path) -> None:
    path = get_metadata_path(tmp_path, CHANNEL, LOCAL_METADATA.version)

    # invalid input
    with pytest.raises(ValueError):
        write_metadata(tmp_path, "defaults", LOCAL_METADATA, tos_accepted=True)

    with pytest.raises(TypeError):
        write_metadata(tmp_path, CHANNEL, object(), tos_accepted=True)  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        write_metadata(tmp_path, CHANNEL, LOCAL_METADATA, tos_accepted=object())

    # write with RemoteToSMetadata
    metadata_pair = write_metadata(
        tmp_path,
        CHANNEL,
        REMOTE_METADATA,
        tos_accepted=True,
    )
    assert isinstance(metadata_pair, LocalPair)
    assert _similar_metadata(metadata_pair.metadata, LOCAL_METADATA)
    assert metadata_pair.path == path

    # write with LocalToSMetadata
    metadata_pair = write_metadata(tmp_path, CHANNEL, LOCAL_METADATA, tos_accepted=True)
    assert isinstance(metadata_pair, LocalPair)
    assert _similar_metadata(metadata_pair.metadata, LOCAL_METADATA)
    assert metadata_pair.path == path

    try:
        path.chmod(0o000)
        with pytest.raises(CondaToSPermissionError):
            write_metadata(tmp_path, CHANNEL, LOCAL_METADATA)
    finally:
        # cleanup so tmp_path can be removed
        path.chmod(0o700)


def test_read_metadata(tmp_path: Path) -> None:
    path = get_metadata_path(tmp_path, CHANNEL, REMOTE_METADATA.version)

    # missing file
    assert not read_metadata(path)

    # corrupt file
    path.parent.mkdir(parents=True)
    path.write_text("corrupt")
    assert not read_metadata(path)

    # invalid JSON schema
    path.write_text("{}")
    assert not read_metadata(path)

    try:
        path.chmod(0o000)
        with nullcontext() if on_win else pytest.raises(CondaToSPermissionError):
            # Windows can only make the path read-only
            read_metadata(path)
    finally:
        # cleanup so tmp_path can be removed
        path.chmod(0o644)

    # valid metadata
    write_metadata(tmp_path, CHANNEL, REMOTE_METADATA, tos_accepted=True)
    assert read_metadata(path)


def test_get_local_metadata(tmp_path: Path) -> None:
    # missing metadata
    with pytest.raises(CondaToSMissingError):
        get_local_metadata(CHANNEL)

    # valid reads
    expected = write_metadata(tmp_path, CHANNEL, REMOTE_METADATA, tos_accepted=True)
    assert get_local_metadata(CHANNEL, extend_search_path=[tmp_path]) == expected

    expected = write_metadata(tmp_path, CHANNEL, REMOTE_METADATA, tos_accepted=False)
    assert get_local_metadata(CHANNEL, extend_search_path=[tmp_path]) == expected


def test_get_local_metadatas(
    mock_search_path: tuple[Path, Path],
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    system_tos_root, user_tos_root = mock_search_path
    monkeypatch.setenv("CONDATOS", str(tmp_path))

    # no metadata
    assert len(list(get_local_metadatas())) == 0

    # $CONDATOS is lowest priority
    expected = write_metadata(tmp_path, CHANNEL, REMOTE_METADATA, tos_accepted=True)
    assert list(get_local_metadatas()) == [(CHANNEL, expected)]

    # user metadata root is higher priority over custom metadata root
    expected = write_metadata(
        user_tos_root,
        CHANNEL,
        REMOTE_METADATA,
        tos_accepted=False,
    )
    assert list(get_local_metadatas()) == [(CHANNEL, expected)]

    # system metadata root is highest priority
    expected = write_metadata(
        system_tos_root,
        CHANNEL,
        REMOTE_METADATA,
        tos_accepted=True,
    )
    assert list(get_local_metadatas()) == [(CHANNEL, expected)]
