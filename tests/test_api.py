# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

from conda.base.context import context
from conda.models.channel import Channel

from anaconda_conda_tos.api import accept_tos, get_channels, get_tos, reject_tos
from anaconda_conda_tos.path import get_metadata_path

if TYPE_CHECKING:
    from pathlib import Path


def test_get_channels() -> None:
    defaults = set(map(Channel, context.default_channels))
    assert set(get_channels("defaults")) == defaults

    conda_forge = {Channel("conda-forge")}
    assert set(get_channels("conda-forge")) == conda_forge

    assert set(get_channels("defaults", "conda-forge")) == defaults | conda_forge


def test_get_tos(
    tos_channel: str,
    sample_channel: str,
    mock_tos_search_path: tuple[Path, Path],
) -> None:
    _, user_tos_root = mock_tos_search_path

    # list all channels and whether their ToS has been accepted
    tos = list(get_tos(tos_channel, sample_channel))
    assert len(tos) == 2
    (channel1, metadata_pair1), (channel2, metadata_pair2) = tos
    assert channel1 == Channel(tos_channel)
    assert not metadata_pair1
    assert channel2 == Channel(sample_channel)
    assert not metadata_pair2

    # accept the ToS for a channel
    accept_tos(user_tos_root, tos_channel)
    tos = list(get_tos(tos_channel, sample_channel))
    assert len(tos) == 2
    (channel1, metadata_pair1), (channel2, metadata_pair2) = tos
    assert channel1 == Channel(tos_channel)
    assert metadata_pair1
    assert metadata_pair1.metadata.tos_accepted
    assert metadata_pair1.path == get_metadata_path(user_tos_root, tos_channel, 1)
    assert channel2 == Channel(sample_channel)
    assert not metadata_pair2

    # list all channels that have been accepted even if it is not active
    accept_tos(user_tos_root, tos_channel)
    tos = list(get_tos())
    assert len(tos) == 1
    channel1, metadata_pair1 = tos[0]
    assert channel1 == Channel(tos_channel)
    assert metadata_pair1
    assert metadata_pair1.metadata.tos_accepted
    assert metadata_pair1.path == get_metadata_path(user_tos_root, tos_channel, 1)

    # even rejected ToS channels are listed
    reject_tos(user_tos_root, tos_channel)
    tos = list(get_tos())
    assert len(tos) == 1
    channel1, metadata_pair1 = tos[0]
    assert channel1 == Channel(tos_channel)
    assert metadata_pair1
    assert not metadata_pair1.metadata.tos_accepted
    assert metadata_pair1.path == get_metadata_path(user_tos_root, tos_channel, 1)
