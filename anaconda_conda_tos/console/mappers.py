# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Mappers to aid in rendering of console output."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import MetadataPathPair


def version_mapping(metadata_pair: MetadataPathPair | None) -> str:
    """Map the ToS version to a human-readable string."""
    if not metadata_pair or metadata_pair.metadata.tos_version is None:
        return "-"
    return str(metadata_pair.metadata.tos_version)


def accepted_mapping(metadata_pair: MetadataPathPair | None) -> str:
    """Map the ToS acceptance status to a human-readable string."""
    if not metadata_pair:
        return "-"

    tos_accepted = metadata_pair.metadata.tos_accepted
    acceptance_timestamp = metadata_pair.metadata.acceptance_timestamp
    if tos_accepted is None:
        # neither accepted nor rejected
        return "-"
    elif tos_accepted:
        if acceptance_timestamp:
            # convert timestamp to localized time
            return acceptance_timestamp.astimezone().isoformat(" ")
        else:
            # accepted but no timestamp
            return "unknown"
    else:
        return "rejected"


def path_mapping(metadata_pair: MetadataPathPair | None) -> str:
    """Map the ToS path to a human-readable string."""
    if not metadata_pair:
        return "-"
    return str(metadata_pair.path.parent.parent)
