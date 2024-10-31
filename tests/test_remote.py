# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from anaconda_conda_tos.exceptions import CondaToSInvalidError, CondaToSMissingError
from anaconda_conda_tos.remote import get_endpoint, get_metadata

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from anaconda_conda_tos.models import RemoteToSMetadata


def test_get_endpoint(tos_channel: str, sample_channel: str) -> None:
    # get ToS endpoint for ToS channel
    assert get_endpoint(tos_channel).status_code == 200

    # no ToS endpoint for sample channel
    with pytest.raises(CondaToSMissingError):
        get_endpoint(sample_channel)

    # invalid channel
    with pytest.raises(ValueError):
        get_endpoint("defaults")

    with pytest.raises(CondaToSMissingError):
        get_endpoint(uuid4().hex)


def test_get_tos_metadata(
    tos_channel: str,
    sample_channel: str,
    tos_metadata: RemoteToSMetadata,
    mocker: MockerFixture,
) -> None:
    # get metadata of ToS channel
    assert get_metadata(tos_channel) == tos_metadata

    # no metadata for sample channel
    with pytest.raises(CondaToSMissingError):
        get_metadata(sample_channel)

    # invalid channel
    with pytest.raises(ValueError):
        get_metadata("defaults")

    with pytest.raises(CondaToSMissingError):
        get_metadata(uuid4().hex)

    mocker.patch("anaconda_conda_tos.remote.get_endpoint", return_value=None)
    with pytest.raises(CondaToSInvalidError):
        get_metadata("channel")

    mocker.patch("anaconda_conda_tos.remote.get_endpoint", return_value=42)
    with pytest.raises(CondaToSInvalidError):
        get_metadata("channel")

    mocker.patch("anaconda_conda_tos.remote.get_endpoint", return_value={})
    with pytest.raises(CondaToSInvalidError):
        get_metadata("channel")
