# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from anaconda_conda_tos.models import LocalToSMetadata, RemoteToSMetadata

if TYPE_CHECKING:
    from typing import Final


@pytest.mark.parametrize(
    "tos_version,text,raises",
    [
        pytest.param(None, None, True, id="missing"),
        pytest.param(1, None, True, id="only tos_version"),
        pytest.param(None, "ToS", True, id="only text"),
        pytest.param(object(), None, True, id="invalid tos_version"),
        pytest.param(None, object(), True, id="invalid text"),
        pytest.param(1, "ToS", False, id="complete"),
    ],
)
def test_RemoteToSMetadata(  # noqa: N802
    tos_version: int | None,
    text: str | None,
    raises: bool,
) -> None:
    remote = {
        "tos_version": tos_version,
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
        pytest.param("url", None, None, False, id="only base_url"),
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
        "tos_version": 1,  # see tests/test_remote.py::test_RemoteToSMetadata
        "text": "ToS",  # see tests/test_remote.py::test_RemoteToSMetadata
        "base_url": base_url,
        "tos_accepted": tos_accepted,
        "acceptance_timestamp": acceptance_timestamp,
    }
    with pytest.raises(ValidationError) if raises else nullcontext():
        LocalToSMetadata(
            **{key: value for key, value in local.items() if value is not None},
        )
