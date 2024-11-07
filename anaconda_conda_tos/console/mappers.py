# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Mappers to aid in rendering of console output."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import RemoteToSMetadata

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

    from ..models import LocalToSMetadata


def timestamp_mapping(timestamp: datetime) -> str:
    """Map the UTC ToS timestamp to a localized human-readable string."""
    return timestamp.astimezone().strftime("%Y-%m-%d")


def accepted_mapping(metadata: RemoteToSMetadata | LocalToSMetadata) -> str:
    """Map the ToS acceptance status to a human-readable string."""
    if isinstance(metadata, RemoteToSMetadata):
        return "-"

    tos_accepted = metadata.tos_accepted
    acceptance_timestamp = metadata.acceptance_timestamp
    if tos_accepted:
        if acceptance_timestamp:
            # convert timestamp to localized time
            return timestamp_mapping(acceptance_timestamp)
        else:
            # accepted but no timestamp
            return "unknown"
    else:
        return "rejected"


def location_mapping(path: Path | None) -> str:
    """Map the ToS path to a human-readable string."""
    if not path:
        return "-"
    return str(path.parent.parent)
