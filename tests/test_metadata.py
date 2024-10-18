# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from conda.models.channel import Channel
from pydantic import ValidationError

from anaconda_conda_tos.metadata import ToSMetadata, write_metadata
from anaconda_conda_tos.path import get_tos_path
from anaconda_conda_tos.remote import RemoteToSMetadata


def test_write_metadata(tos_channel: str) -> None:
    channel = Channel(tos_channel)
    now = datetime.now(tz=timezone.utc).timestamp()
    remote_metadata = RemoteToSMetadata(tos_version=42, **{uuid4().hex: uuid4().hex})
    metadata = ToSMetadata(
        **remote_metadata.model_dump(),
        tos_accepted=True,
        # the following fields are overridden in write_metadata
        acceptance_timestamp=now,
        base_url=channel.base_url,
    )

    with pytest.raises(ValueError):
        write_metadata("defaults", metadata)

    write_metadata(tos_channel, metadata)

    with pytest.raises(TypeError):
        write_metadata(tos_channel, "metadata")  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        write_metadata(tos_channel, remote_metadata)

    write_metadata(tos_channel, remote_metadata, tos_accepted=True)

    with pytest.raises(ValidationError):
        write_metadata(tos_channel, remote_metadata)

    write_metadata(tos_channel, metadata)
    contents = get_tos_path(tos_channel, 42).read_text()
    local_metadata = ToSMetadata.model_validate_json(contents)
    assert local_metadata.model_fields == metadata.model_fields
    assert all(
        getattr(local_metadata, key) == getattr(metadata, key)
        for key in set(local_metadata.model_fields) - {"acceptance_timestamp"}
    )
