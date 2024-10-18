# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from conda.models.channel import Channel

from anaconda_conda_tos.metadata import write_metadata
from anaconda_conda_tos.path import get_tos_path


def test_write_metadata(tos_channel: str) -> None:
    channel = Channel(tos_channel)
    now = datetime.now(tz=timezone.utc).timestamp()
    metadata = {
        uuid4().hex: uuid4().hex,
        "tos_version": 42,
        "tos_accepted": True,
        "acceptance_timestamp": now,
    }

    with pytest.raises(ValueError):
        write_metadata("defaults", **metadata)  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        write_metadata(tos_channel, **{**metadata, "tos_version": "1"})  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        write_metadata(tos_channel, **{**metadata, "acceptance_timestamp": "0"})  # type: ignore[arg-type]

    write_metadata(tos_channel, **metadata)  # type: ignore[arg-type]
    assert json.loads(get_tos_path(tos_channel, 42).read_text()) == {
        **metadata,
        "base_url": channel.base_url,
    }
