# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS metadata models."""

from __future__ import annotations

from datetime import datetime  # noqa: TCH003 # needed for Pydantic model
from pathlib import Path  # noqa: TCH003 # needed for Pydantic model
from typing import TYPE_CHECKING, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

if TYPE_CHECKING:
    from typing import Self


class RemoteToSMetadata(BaseModel):
    """Conda ToS metadata schema for the remote endpoint."""

    model_config = ConfigDict(extra="allow")
    tos_version: int
    text: str


class LocalToSMetadata(RemoteToSMetadata):
    """Conda ToS metadata schema with acceptance fields."""

    base_url: str
    # FUTURE: Python 3.10+, switch to `bool | None`
    tos_accepted: Optional[bool] = Field(None)  # noqa: UP007
    # FUTURE: Python 3.10+, switch to `datetime | None`
    acceptance_timestamp: Optional[datetime] = Field(None)  # noqa: UP007

    @model_validator(mode="after")
    def _required(self: Self) -> Self:
        if (self.tos_accepted is None) is not (self.acceptance_timestamp is None):
            raise ValueError(
                "`tos_accepted` and `acceptance_timestamp` must be provided together."
            )
        return self


class MetadataPathPair(BaseModel):
    """Tuple of ToS metadata and path."""

    # FUTURE: Python 3.10+, switch to `LocalToSMetadata | RemoteToSMetadata`
    metadata: Union[LocalToSMetadata, RemoteToSMetadata]  # noqa: UP007
    # FUTURE: Python 3.10+, switch to `Path | None`
    path: Optional[Path] = Field(None)  # noqa: UP007

    @model_validator(mode="after")
    def _required(self: Self) -> Self:
        if type(self.metadata) is RemoteToSMetadata:
            self.path = None
        elif type(self.metadata) is LocalToSMetadata and not self.path:
            raise ValueError(
                "`path` must be provided when metadata is a LocalToSMetadata."
            )
        return self

    def __lt__(self: Self, other: MetadataPathPair) -> bool:
        """Compare the ToS metadata version.

        Critical for sorting a list of ToS metadata path pairs.
        """
        if not isinstance(other, MetadataPathPair):
            return NotImplemented

        # we sort in reverse here to list the highest version first,
        # this also ensures we do not mess with the priority order
        return self.metadata.tos_version > other.metadata.tos_version
