# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda ToS metadata models."""

from __future__ import annotations

from datetime import datetime  # noqa: TCH003 # needed for pydantic model
from typing import TYPE_CHECKING

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
    tos_accepted: bool | None = Field(None)
    acceptance_timestamp: datetime | None = Field(None)

    @model_validator(mode="after")
    def _required(self: Self) -> Self:
        if (self.tos_accepted is None) is not (self.acceptance_timestamp is None):
            raise ValueError(
                "`tos_accepted` and `acceptance_timestamp` must be provided together."
            )
        return self
