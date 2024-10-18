# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from uuid import uuid4

import pytest

from anaconda_conda_tos.exceptions import CondaToSMissingError
from anaconda_conda_tos.remote import (
    TOS_TEXT_ENDPOINT,
    get_tos_endpoint,
    get_tos_metadata,
    get_tos_text,
)


def test_get_tos_endpoint(tos_channel: str, sample_channel: str) -> None:
    # get ToS endpoint for ToS channel
    assert get_tos_endpoint(tos_channel, TOS_TEXT_ENDPOINT).status_code == 200

    # no ToS endpoint for sample channel
    with pytest.raises(CondaToSMissingError):
        get_tos_endpoint(sample_channel, TOS_TEXT_ENDPOINT)

    # invalid channel
    with pytest.raises(ValueError):
        get_tos_endpoint("defaults", TOS_TEXT_ENDPOINT)

    with pytest.raises(CondaToSMissingError):
        get_tos_endpoint(uuid4().hex, TOS_TEXT_ENDPOINT)

    # invalid endpoint
    with pytest.raises(ValueError):
        get_tos_endpoint(sample_channel, "invalid")  # type: ignore[arg-type]


def test_get_tos_text(
    tos_channel: str,
    sample_channel: str,
    tos_full_lines: list[str],
) -> None:
    # get full text of ToS channel
    assert get_tos_text(tos_channel).splitlines() == tos_full_lines

    # no full text for sample channel
    with pytest.raises(CondaToSMissingError):
        get_tos_text(sample_channel)

    # invalid channel
    with pytest.raises(ValueError):
        get_tos_text("defaults")

    with pytest.raises(CondaToSMissingError):
        get_tos_text(uuid4().hex)


def test_get_tos_metadata(
    tos_channel: str,
    sample_channel: str,
    tos_metadata: dict,
) -> None:
    # get metadata of ToS channel
    assert get_tos_metadata(tos_channel) == tos_metadata

    # no metadata for sample channel
    with pytest.raises(CondaToSMissingError):
        get_tos_metadata(sample_channel)

    # invalid channel
    with pytest.raises(ValueError):
        get_tos_metadata("defaults")

    with pytest.raises(CondaToSMissingError):
        get_tos_metadata(uuid4().hex)
