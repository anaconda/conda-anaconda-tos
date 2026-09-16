# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from datetime import timedelta
from io import StringIO
from typing import TYPE_CHECKING

import pytest
from requests import Response
from requests.exceptions import ConnectionError as RequestConnectionError
from requests.exceptions import HTTPError, Timeout
from rich.console import Console

from conda_anaconda_tos import remote
from conda_anaconda_tos.api import collect_channel_consent
from conda_anaconda_tos.console import render
from conda_anaconda_tos.exceptions import (
    CondaToSInvalidError,
    CondaToSMissingError,
    CondaToSUnavailableError,
)
from conda_anaconda_tos.local import get_local_metadata, write_metadata
from conda_anaconda_tos.remote import write_cached_endpoint

if TYPE_CHECKING:
    from pathlib import Path

    from conda.models.channel import Channel
    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture

    from conda_anaconda_tos.models import RemoteToSMetadata


pytestmark = pytest.mark.usefixtures("mock_search_path")


def test_empty_selection_does_not_inherit_context_channels(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    inspect = mocker.spy(render, "get_one_tos")
    assert collect_channel_consent(tos_root=tmp_path, cache_timeout=0) == {}
    inspect.assert_not_called()


def test_missing_terms_are_not_required(
    sample_channel: Channel, tmp_path: Path
) -> None:
    assert collect_channel_consent(
        sample_channel,
        tos_root=tmp_path,
        cache_timeout=0,
    ) == {sample_channel.base_url: "not-required"}


@pytest.mark.parametrize("interactive", (False, True))
def test_ci_and_automatic_settings_do_not_grant_consent(
    tos_channel: Channel,
    tmp_path: Path,
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
    interactive: bool,
) -> None:
    monkeypatch.setenv("CONDA_PLUGINS_AUTO_ACCEPT_TOS", "true")
    mocker.patch("conda_anaconda_tos.console.render.CI", True)
    mocker.patch("conda_anaconda_tos.console.render.IS_INTERACTIVE", False)
    mocker.patch(
        "conda.base.context.Context.always_yes",
        new_callable=mocker.PropertyMock,
        return_value=True,
    )
    prompt = mocker.patch("conda_anaconda_tos.console.render._prompt_acceptance")

    assert collect_channel_consent(
        tos_channel,
        tos_root=tmp_path,
        cache_timeout=0,
        interactive=interactive,
    ) == {tos_channel.base_url: "required"}

    prompt.assert_not_called()
    with pytest.raises(CondaToSMissingError):
        get_local_metadata(tos_channel, extend_search_path=[tmp_path])


@pytest.mark.parametrize("accepted", (False, True))
def test_existing_decision_is_reported_without_prompt(
    tos_channel: Channel,
    tos_metadata: RemoteToSMetadata,
    tmp_path: Path,
    mocker: MockerFixture,
    accepted: bool,
) -> None:
    write_metadata(tmp_path, tos_channel, tos_metadata, tos_accepted=accepted)
    prompt = mocker.patch("conda_anaconda_tos.console.render._prompt_acceptance")
    assert collect_channel_consent(
        tos_channel,
        tos_root=tmp_path,
        cache_timeout=0,
        interactive=True,
    ) == {tos_channel.base_url: "accepted" if accepted else "rejected"}
    prompt.assert_not_called()


@pytest.mark.parametrize("accepted", (False, True))
def test_interactive_consent_uses_provider_prompt_and_persists_exact_version(
    tos_channel: Channel,
    tos_metadata: RemoteToSMetadata,
    tmp_path: Path,
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
    accepted: bool,
) -> None:
    reviewed_version = tos_metadata.version
    mocker.patch("conda_anaconda_tos.console.render.IS_INTERACTIVE", True)
    mocker.patch("conda_anaconda_tos.console.render.JUPYTER", False)
    mocker.patch("conda_anaconda_tos.console.render.CI", True)

    def answer(*_args: object, **_kwargs: object) -> str:
        monkeypatch.setattr(
            tos_metadata, "version", reviewed_version + timedelta(days=1)
        )
        return "accept" if accepted else "reject"

    prompt = mocker.patch(
        "conda_anaconda_tos.console.render.FuzzyPrompt.ask", side_effect=answer
    )
    assert collect_channel_consent(
        tos_channel,
        tos_root=tmp_path,
        cache_timeout=0,
        interactive=True,
        console=Console(file=StringIO()),
    ) == {tos_channel.base_url: "accepted" if accepted else "rejected"}

    prompt.assert_called_once()
    stored = get_local_metadata(tos_channel, extend_search_path=[tmp_path])
    assert stored.metadata.version == reviewed_version
    assert stored.metadata.tos_accepted is accepted
    assert collect_channel_consent(
        tos_channel,
        tos_root=tmp_path,
        cache_timeout=0,
    ) == {tos_channel.base_url: "required"}


def test_interactive_view_shows_terms_before_acceptance(
    tos_channel: Channel,
    tos_metadata: RemoteToSMetadata,
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    mocker.patch("conda_anaconda_tos.console.render.IS_INTERACTIVE", True)
    mocker.patch("conda_anaconda_tos.console.render.JUPYTER", False)
    prompt = mocker.patch(
        "conda_anaconda_tos.console.render.FuzzyPrompt.ask",
        side_effect=["view", "accept"],
    )
    output = StringIO()

    result = collect_channel_consent(
        tos_channel,
        tos_root=tmp_path,
        cache_timeout=0,
        interactive=True,
        console=Console(file=output),
    )

    assert result == {tos_channel.base_url: "accepted"}
    assert tos_metadata.text in output.getvalue()
    assert prompt.call_count == 2


@pytest.mark.parametrize("error", (RequestConnectionError, Timeout))
def test_network_failure_does_not_fall_back_to_local_acceptance(
    tos_channel: Channel,
    tos_metadata: RemoteToSMetadata,
    tmp_path: Path,
    mocker: MockerFixture,
    error: type[Exception],
) -> None:
    write_metadata(tmp_path, tos_channel, tos_metadata, tos_accepted=True)
    mocker.patch(
        "conda_anaconda_tos.remote.get_session"
    ).return_value.get.side_effect = error()

    with pytest.raises(CondaToSUnavailableError):
        collect_channel_consent(tos_channel, tos_root=tmp_path, cache_timeout=0)


def test_session_offline_failure_does_not_cache_missing_terms(
    tos_channel: Channel,
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "conda_anaconda_tos.remote.get_session"
    ).return_value.get.side_effect = RuntimeError("EnforceUnusedAdapter offline mode")
    write_cache = mocker.spy(remote, "write_cached_endpoint")

    with pytest.raises(CondaToSUnavailableError):
        collect_channel_consent(tos_channel, tos_root=tmp_path, cache_timeout=0)

    write_cache.assert_not_called()


@pytest.mark.parametrize("status", (401, 403, 407, 500, 503))
def test_http_failure_does_not_become_missing_terms(
    tmp_path: Path,
    mocker: MockerFixture,
    status: int,
) -> None:
    response = Response()
    response.status_code = status
    mocker.patch(
        "conda_anaconda_tos.remote.get_session"
    ).return_value.get.side_effect = HTTPError(response=response)

    with pytest.raises(CondaToSUnavailableError):
        collect_channel_consent(
            "https://repo.example.com/research", tos_root=tmp_path, cache_timeout=0
        )


@pytest.mark.parametrize("status", (404, 410))
def test_provider_required_host_cannot_bypass_missing_metadata(
    tmp_path: Path,
    mocker: MockerFixture,
    status: int,
) -> None:
    response = Response()
    response.status_code = status
    mocker.patch(
        "conda_anaconda_tos.remote.get_session"
    ).return_value.get.side_effect = HTTPError(response=response)

    with pytest.raises(CondaToSUnavailableError):
        collect_channel_consent(
            "https://repo.anaconda.com/pkgs/main", tos_root=tmp_path, cache_timeout=0
        )


@pytest.mark.parametrize("payload", (b"invalid-json", b'{"version": "invalid"}'))
def test_invalid_metadata_does_not_become_missing_terms(
    tmp_path: Path,
    mocker: MockerFixture,
    payload: bytes,
) -> None:
    response = Response()
    response.status_code = 200
    response._content = payload
    mocker.patch(
        "conda_anaconda_tos.remote.get_session"
    ).return_value.get.return_value = response

    with pytest.raises(CondaToSInvalidError):
        collect_channel_consent(
            "https://repo.example.com/research", tos_root=tmp_path, cache_timeout=0
        )


def test_empty_legacy_cache_is_rechecked(tos_channel: Channel, tmp_path: Path) -> None:
    write_cached_endpoint(tos_channel, None)
    assert collect_channel_consent(
        tos_channel,
        tos_root=tmp_path,
        cache_timeout=float("inf"),
    ) == {tos_channel.base_url: "required"}


def test_invalid_response_cannot_refresh_old_accepted_metadata(
    tos_channel: Channel,
    tos_metadata: RemoteToSMetadata,
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    write_metadata(tmp_path, tos_channel, tos_metadata, tos_accepted=True)
    write_cached_endpoint(tos_channel, tos_metadata)
    response = Response()
    response.status_code = 200
    response._content = b"invalid-json"
    mocker.patch(
        "conda_anaconda_tos.remote.get_session"
    ).return_value.get.return_value = response

    for timeout in (0, float("inf")):
        with pytest.raises(CondaToSInvalidError):
            collect_channel_consent(
                tos_channel, tos_root=tmp_path, cache_timeout=timeout
            )


@pytest.mark.parametrize("status", (404, 410))
def test_confirmed_missing_endpoint_does_not_require_consent(
    tmp_path: Path,
    mocker: MockerFixture,
    status: int,
) -> None:
    response = Response()
    response.status_code = status
    mocker.patch(
        "conda_anaconda_tos.remote.get_session"
    ).return_value.get.side_effect = HTTPError(response=response)
    channel = "https://repo.example.com/research"

    assert collect_channel_consent(channel, tos_root=tmp_path, cache_timeout=0) == {
        channel: "not-required",
    }


def test_offline_strict_lookup_respects_cache_timeout(
    tos_channel: Channel,
    tos_metadata: RemoteToSMetadata,
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    write_cached_endpoint(tos_channel, tos_metadata)
    write_metadata(tmp_path, tos_channel, tos_metadata, tos_accepted=True)
    mocker.patch(
        "conda.base.context.Context.offline",
        new_callable=mocker.PropertyMock,
        return_value=True,
    )

    with pytest.raises(CondaToSUnavailableError):
        collect_channel_consent(tos_channel, tos_root=tmp_path, cache_timeout=0)

    assert collect_channel_consent(
        tos_channel,
        tos_root=tmp_path,
        cache_timeout=float("inf"),
    ) == {tos_channel.base_url: "accepted"}
