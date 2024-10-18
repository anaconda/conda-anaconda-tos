# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from pathlib import Path

import pytest
from conda.base.context import context

from anaconda_conda_tos.path import (
    TOS_DIRECTORY,
    get_tos_dir,
    get_tos_path,
    hash_channel,
)


def test_hash_channel(sample_channel: str, tos_channel: str) -> None:
    assert hash_channel(sample_channel) == hash_channel(sample_channel)
    assert hash_channel(sample_channel) != hash_channel(tos_channel)

    # invalid channel
    with pytest.raises(ValueError):
        hash_channel("defaults")


def test_get_tos_dir(sample_channel: str) -> None:
    assert get_tos_dir(sample_channel) == Path(
        context.target_prefix,
        TOS_DIRECTORY,
        hash_channel(sample_channel),
    )


def test_get_tos_path(sample_channel: str) -> None:
    assert get_tos_path(sample_channel, 42) == get_tos_dir(sample_channel) / "42.json"
