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
    from typing import Final


@pytest.mark.parametrize(
    "version,text,raises",
    [
        pytest.param(None, None, True, id="missing"),
        pytest.param(1, None, True, id="only version"),
        pytest.param(None, "ToS", True, id="only text"),
        pytest.param(object(), None, True, id="invalid version"),
        pytest.param(None, object(), True, id="invalid text"),
        pytest.param(1, "ToS", False, id="complete"),
    ],
)
def test_RemoteToSMetadata(  # noqa: N802
    version: int | None,
    text: str | None,
    raises: bool,
) -> None:
    remote = {
        "version": version,
        "text": text,
    }
    with pytest.raises(ValidationError) if raises else nullcontext():
        RemoteToSMetadata(
            **{key: value for key, value in remote.items() if value is not None},
        )


NOW: Final = datetime.now(tz=timezone.utc)


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
    local = {
        "version": 1,  # tested in test_RemoteToSMetadata
        "text": "ToS",  # tested in test_RemoteToSMetadata
        "base_url": base_url,
        "tos_accepted": tos_accepted,
        "acceptance_timestamp": acceptance_timestamp,
    }
    with pytest.raises(ValidationError) if raises else nullcontext():
        LocalToSMetadata(
            **{key: value for key, value in local.items() if value is not None},
        )


REMOTE_METADATA = RemoteToSMetadata(version=2, text="ToS")
LOCAL_METADATA = LocalToSMetadata(
    version=1,
    text="ToS",
    base_url="url",
    tos_accepted=True,
    acceptance_timestamp=NOW,
)


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
    kwargs = {key: value for key, value in kwargs.items() if value is not None}
    with pytest.raises(ValidationError) if raises else nullcontext():
        RemotePair(**kwargs)


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
    kwargs = {key: value for key, value in kwargs.items() if value is not None}
    with pytest.raises(ValidationError) if raises else nullcontext():
        LocalPair(**kwargs)


def test_MetadataPair_lt() -> None:  # noqa: N802
    local = LocalPair(metadata=LOCAL_METADATA, path="path")
    remote = RemotePair(metadata=REMOTE_METADATA)
    assert local < remote

    with pytest.raises(TypeError):
        assert object() > local
    with pytest.raises(TypeError):
        assert object() > remote
