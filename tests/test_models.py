# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from anaconda_conda_tos.models import (
    LocalPair,
    LocalToSMetadata,
    RemotePair,
    RemoteToSMetadata,
)

if TYPE_CHECKING:
    from typing import Any, Final

TIMESTAMP1: Final = datetime(2024, 10, 1, tzinfo=timezone.utc)  # "version 1"
TIMESTAMP2: Final = datetime(2024, 11, 1, tzinfo=timezone.utc)  # "version 2"
NOW: Final = datetime.now(tz=timezone.utc)
REMOTE_METADATA = RemoteToSMetadata(timestamp=TIMESTAMP2, text="ToS")
LOCAL_METADATA = LocalToSMetadata(
    timestamp=TIMESTAMP1,
    text="ToS",
    base_url="url",
    tos_accepted=True,
    acceptance_timestamp=NOW,
)


def _filter_none_keys(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in kwargs.items() if value is not None}


@pytest.mark.parametrize(
    "timestamp,text,raises",
    [
        pytest.param(None, None, True, id="missing"),
        pytest.param(TIMESTAMP1, None, True, id="only timestamp"),
        pytest.param(None, "ToS", True, id="only text"),
        pytest.param(object(), None, True, id="invalid timestamp"),
        pytest.param(None, object(), True, id="invalid text"),
        pytest.param(TIMESTAMP1, "ToS", False, id="complete"),
    ],
)
def test_RemoteToSMetadata(  # noqa: N802
    timestamp: datetime | None,
    text: str | None,
    raises: bool,
) -> None:
    kwargs = {"timestamp": timestamp, "text": text}
    with pytest.raises(ValidationError) if raises else nullcontext():
        RemoteToSMetadata(**_filter_none_keys(kwargs))


@pytest.mark.parametrize(
    "base_url,tos_accepted,acceptance_timestamp,raises",
    [
        pytest.param(None, None, None, True, id="missing"),
        pytest.param("url", None, None, True, id="only base_url"),
        pytest.param(None, True, None, True, id="only tos_accepted"),
        pytest.param(None, None, NOW, True, id="only acceptance_timestamp"),
        pytest.param(object(), None, None, True, id="invalid base_url"),
        pytest.param(None, object(), None, True, id="invalid tos_accepted"),
        pytest.param(None, None, object(), True, id="invalid acceptance_timestamp"),
        pytest.param("url", True, None, True, id="base_url & tos_accepted"),
        pytest.param(None, True, NOW, True, id="tos_accepted & acceptance_timestamp"),
        pytest.param("url", None, NOW, True, id="base_url & acceptance_timestamp"),
        pytest.param("url", True, NOW, False, id="complete"),
    ],
)
def test_LocalToSMetadata(  # noqa: N802
    base_url: str | None,
    tos_accepted: bool | None,
    acceptance_timestamp: datetime | None,
    raises: bool,
) -> None:
    kwargs = {
        "timestamp": TIMESTAMP1,  # tested in test_RemoteToSMetadata
        "text": "ToS",  # tested in test_RemoteToSMetadata
        "base_url": base_url,
        "tos_accepted": tos_accepted,
        "acceptance_timestamp": acceptance_timestamp,
    }
    with pytest.raises(ValidationError) if raises else nullcontext():
        LocalToSMetadata(**_filter_none_keys(kwargs))


def test_ToSMetadata_ge() -> None:  # noqa: N802
    assert REMOTE_METADATA >= LOCAL_METADATA

    with pytest.raises(TypeError):
        assert object() <= REMOTE_METADATA
    with pytest.raises(TypeError):
        assert object() <= LOCAL_METADATA


@pytest.mark.parametrize(
    "metadata,path,raises",
    [
        pytest.param(None, None, True, id="missing"),
        pytest.param(REMOTE_METADATA, None, False, id="only metadata"),
        pytest.param(None, "path", True, id="only path"),
        pytest.param(REMOTE_METADATA, "path", True, id="complete"),
    ],
)
def test_RemotePair(  # noqa: N802
    metadata: RemoteToSMetadata | None,
    path: str | None,
    raises: bool,
) -> None:
    kwargs = {"metadata": metadata, "path": path}
    with pytest.raises(ValidationError) if raises else nullcontext():
        RemotePair(**_filter_none_keys(kwargs))


@pytest.mark.parametrize(
    "metadata,path,raises",
    [
        pytest.param(None, None, True, id="missing"),
        pytest.param(LOCAL_METADATA, None, True, id="only metadata"),
        pytest.param(None, "path", True, id="only path"),
        pytest.param(LOCAL_METADATA, "path", False, id="complete"),
    ],
)
def test_LocalPair(  # noqa: N802
    metadata: RemoteToSMetadata | None,
    path: str | None,
    raises: bool,
) -> None:
    kwargs = {"metadata": metadata, "path": path}
    with pytest.raises(ValidationError) if raises else nullcontext():
        LocalPair(**_filter_none_keys(kwargs))


def test_MetadataPair_lt() -> None:  # noqa: N802
    local = LocalPair(metadata=LOCAL_METADATA, path="path")
    remote = RemotePair(metadata=REMOTE_METADATA)
    assert local < remote

    with pytest.raises(TypeError):
        assert object() > local
    with pytest.raises(TypeError):
        assert object() > remote
