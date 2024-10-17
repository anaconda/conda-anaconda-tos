# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from conda.exceptions import CondaError
from conda.models.channel import Channel


class CondaToSError(CondaError):
    pass


class CondaToSMissing(CondaToSError):
    def __init__(self, channel: str | Channel) -> None:
        super().__init__(f"No ToS for {Channel(channel).base_url or channel}.")
