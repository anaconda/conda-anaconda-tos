# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import nullcontext
from typing import TYPE_CHECKING

import pytest
from rich.prompt import InvalidResponse

from conda_anaconda_tos.console.prompt import FuzzyPrompt

if TYPE_CHECKING:
    from typing import Self

VALID_YES = ["yes", "y", "ye", "(y)es"]
VALID_NO = ["no", "n", "(n)o"]
INVALID = ["nope", "yep", "yessir", "other"]


@pytest.mark.parametrize("response", [*VALID_YES, *VALID_NO, *INVALID])
def test_FuzzyPrompt_no_choices(response: str) -> None:  # noqa: N802
    prompt = FuzzyPrompt("prompt")
    assert prompt.process_response(response) == response


@pytest.mark.parametrize(
    "response,expected",
    [
        *[(response, "yes") for response in VALID_YES],
        *[(response, "no") for response in VALID_NO],
        *[(response, None) for response in INVALID],
    ],
)
def test_FuzzyPrompt_with_choices(response: str, expected: str | None) -> None:  # noqa: N802
    prompt = FuzzyPrompt("prompt", choices=["(y)es", "(n)o"])
    with nullcontext() if expected else pytest.raises(InvalidResponse):
        assert prompt.process_response(response) == expected


def test_FuzzyPrompt_invalid() -> None:  # noqa: N802
    class Unstringable(str):
        def __str__(self: Self) -> str:
            raise ValueError

    prompt = FuzzyPrompt("prompt")
    with pytest.raises(InvalidResponse):
        prompt.process_response(Unstringable())
