# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import argparse
import json
import sys
from contextlib import suppress
from io import StringIO
from typing import TYPE_CHECKING

import pytest
from conda import __version__ as CONDA_VERSION  # noqa: N812
from conda.base.context import context
from conda.common.url import urlparse
from conda.core import index as channel_index
from conda.core.subdir_data import SubdirData
from conda.gateways.connection.session import get_session
from conda.models.channel import Channel
from packaging import version
from requests import Request

from conda_anaconda_tos import plugin
from conda_anaconda_tos.api import (
    accept_tos,
    clean_tos,
    collect_channel_consent,
    reject_tos,
)
from conda_anaconda_tos.console import render
from conda_anaconda_tos.exceptions import (
    CondaToSMissingError,
    CondaToSNonInteractiveError,
    CondaToSRejectedError,
    CondaToSUnavailableError,
)
from conda_anaconda_tos.local import get_local_metadata, write_metadata
from conda_anaconda_tos.path import USER_TOS_ROOT
from conda_anaconda_tos.plugin import (
    conda_request_headers,
    conda_settings,
    conda_subcommands,
    configure_parser,
)

if TYPE_CHECKING:
    from pathlib import Path

    from conda.testing.fixtures import CondaCLIFixture
    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture

    from conda_anaconda_tos.models import RemoteToSMetadata


if version.parse(CONDA_VERSION).release < (25, 1):

    def reset_context() -> None:
        from conda.base.context import reset_context

        reset_context()

        # clear cached property
        with suppress(AttributeError):
            del context.plugins
else:
    from conda.base.context import reset_context  # type: ignore[no-redef]


def test_subcommands_hook() -> None:
    subcommands = list(conda_subcommands())
    assert len(subcommands) == 1

    assert subcommands[0].name == "tos"

    assert "tos" in context.plugin_manager.get_subcommands()


def test_settings_hook() -> None:
    settings = list(conda_settings())
    assert len(settings) == 1

    assert settings[0].name == "auto_accept_tos"


def test_request_headers_hook() -> None:
    host, path = "conda.anaconda.org", "/pkgs/main/terms.json"
    assert not list(conda_request_headers(host, path))

    host, path = "repo.anaconda.com", "/pkgs/main/terms.json"
    assert not list(conda_request_headers(host, path))

    host, path = "repo.anaconda.com", "/pkgs/main/repodata.json"
    headers = list(conda_request_headers(host, path))
    assert len(headers) == 1
    assert headers[0].name.lower() == "anaconda-tos-accept"


def test_subcommand_tos(conda_cli: CondaCLIFixture) -> None:
    out, err, code = conda_cli("tos")
    assert out
    # assert not err  # server log is output to stderr
    assert not code


def test_subcommand_tos_view(
    conda_cli: CondaCLIFixture,
    tos_channel: Channel,
    tos_metadata: RemoteToSMetadata,
    sample_channel: Channel,
    mock_channels: tuple[Channel, Channel],
) -> None:
    tos_channel, sample_channel = mock_channels

    out, err, code = conda_cli("tos", "view")
    assert out.splitlines() == [
        f"viewing Terms of Service for {tos_channel}:",
        *tos_metadata.text.splitlines(),
        f"no Terms of Service for {sample_channel}",
    ]
    # assert not err  # server log is output to stderr
    assert not code


def test_subcommand_tos_accept(
    conda_cli: CondaCLIFixture,
    mock_channels: tuple[Channel, Channel],
    tmp_path: Path,
) -> None:
    tos_channel, sample_channel = mock_channels

    out, err, code = conda_cli("tos", "accept", f"--tos-root={tmp_path}")
    assert out.splitlines() == [
        f"accepted Terms of Service for {tos_channel}",
        f"Terms of Service not found for {sample_channel}",
    ]
    # assert not err  # server log is output to stderr
    assert not code


def test_subcommand_tos_reject(
    conda_cli: CondaCLIFixture,
    mock_channels: tuple[Channel, Channel],
    tmp_path: Path,
) -> None:
    tos_channel, sample_channel = mock_channels

    out, err, code = conda_cli("tos", "reject", f"--tos-root={tmp_path}")
    assert out.splitlines() == [
        f"rejected Terms of Service for {tos_channel}",
        f"Terms of Service not found for {sample_channel}",
    ]
    # assert not err  # server log is output to stderr
    assert not code


def test_subcommand_tos_list(
    conda_cli: CondaCLIFixture,
    mock_channels: tuple[Channel, Channel],
    mock_search_path: tuple[Path, Path],
    terminal_width: int,  # noqa: ARG001
) -> None:
    system_tos_root, user_tos_root = mock_search_path
    tos_channel, sample_channel = mock_channels

    out, err, code = conda_cli("tos")
    assert tos_channel.base_url in out
    assert sample_channel.base_url in out
    # assert not err  # server log is output to stderr
    assert not code

    accept_tos(tos_channel, tos_root=system_tos_root, cache_timeout=None)
    out, err, code = conda_cli("tos")
    assert tos_channel.base_url in out
    assert sample_channel.base_url in out
    # assert not err  # server log is output to stderr
    assert not code

    reject_tos(tos_channel, tos_root=user_tos_root, cache_timeout=None)
    out, err, code = conda_cli("tos")
    assert tos_channel.base_url in out
    assert sample_channel.base_url in out
    # assert not err  # server log is output to stderr
    assert not code


def test_subcommand_tos_interactive(
    monkeypatch: MonkeyPatch,
    conda_cli: CondaCLIFixture,
    tos_channel: Channel,
    sample_channel: Channel,
    mock_search_path: tuple[Path, Path],
) -> None:
    monkeypatch.setattr(render, "IS_INTERACTIVE", True)

    system_tos_root, user_tos_root = mock_search_path

    monkeypatch.setattr(sys, "stdin", StringIO("accept\n"))
    out, err, code = conda_cli("tos", "interactive", f"--tos-root={user_tos_root}")
    assert tos_channel.base_url in out
    assert sample_channel.base_url not in out
    # assert not err  # server log is output to stderr
    assert not code


def test_subcommand_tos_interactive_offline(
    monkeypatch: MonkeyPatch,
    conda_cli: CondaCLIFixture,
    mock_search_path: tuple[Path, Path],
) -> None:
    # FUTURE: conda 25.1+, remove special reset_context
    reset_context()

    system_tos_root, user_tos_root = mock_search_path

    monkeypatch.setenv("CONDA_OFFLINE", "true")
    reset_context()
    assert context.offline

    out, err, code = conda_cli("tos", "interactive", f"--tos-root={user_tos_root}")
    assert not out
    # assert not err  # server log is output to stderr
    assert not code


@pytest.mark.parametrize("ci", [True, False])
def test_request_headers(
    monkeypatch: MonkeyPatch,
    tos_channel: Channel,
    mock_search_path: tuple[Path, Path],
    tos_metadata: RemoteToSMetadata,
    ci: bool,
) -> None:
    monkeypatch.setattr(plugin, "CI", ci)
    monkeypatch.setattr(plugin, "HOSTS", {urlparse(tos_channel.base_url).netloc})
    system_tos_root, user_tos_root = mock_search_path

    url = f"{tos_channel}/terms.json"

    context.plugin_manager.get_cached_request_headers.cache_clear()
    request = get_session(url).get(url).request
    assert "Anaconda-ToS-Accept" not in request.headers

    url = f"{tos_channel}/repodata.json"

    context.plugin_manager.get_cached_request_headers.cache_clear()
    request = get_session(url).get(url).request
    if ci:
        assert request.headers["Anaconda-ToS-Accept"] == "CI=true"
    else:
        assert request.headers["Anaconda-ToS-Accept"] == ""

    accept_tos(tos_channel, tos_root=user_tos_root, cache_timeout=None)
    request = get_session(url).get(url).request
    value = f"{tos_channel}={int(tos_metadata.version.timestamp())}=accepted="
    assert request.headers["Anaconda-ToS-Accept"].startswith(value)
    if ci:
        assert request.headers["Anaconda-ToS-Accept"].endswith(";CI=true")

    reject_tos(tos_channel, tos_root=user_tos_root, cache_timeout=None)
    request = get_session(url).get(url).request
    value = f"{tos_channel}={int(tos_metadata.version.timestamp())}=rejected="
    assert request.headers["Anaconda-ToS-Accept"].startswith(value)
    if ci:
        assert request.headers["Anaconda-ToS-Accept"].endswith(";CI=true")


def test_conda_search_interactive(
    conda_cli: CondaCLIFixture,
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Conda commands should trigger the interactive TOS prompts."""
    # FUTURE: conda 25.1+, remove special reset_context
    reset_context()

    monkeypatch.setattr(render, "IS_INTERACTIVE", True)
    monkeypatch.setattr(plugin, "DEFAULT_TOS_ROOT", tmp_path)

    # interactive accept
    monkeypatch.setattr(sys, "stdin", StringIO("accept\n"))
    out, _, code = conda_cli("search", "small-executable")
    assert not code

    # FUTURE: conda 25.1+, remove special reset_context
    reset_context()

    # search for package with TOS plugin enabled
    out, _, code = conda_cli("search", "*")
    assert not code
    assert "small-executable" in out

    # search for package with TOS plugin disabled
    monkeypatch.setenv("CONDA_NO_PLUINS", "true")
    reset_context()
    assert not context.no_plugins
    out, _, code = conda_cli("search", "small-executable")
    assert not code
    assert "small-executable"


def test_conda_search_json(
    conda_cli: CondaCLIFixture,
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """JSON output with TOS plugin should be identical to without."""
    # FUTURE: conda 25.1+, remove special reset_context
    reset_context()

    monkeypatch.setattr(plugin, "DEFAULT_TOS_ROOT", tmp_path)

    # accept TOS
    _, _, code = conda_cli("tos", "accept", f"--tos-root={tmp_path}")
    assert not code

    # search for package with TOS plugin enabled
    out, _, code = conda_cli("search", "small-executable", "--json")
    assert not code

    try:
        plugin_enabled = json.loads(out)
    except json.JSONDecodeError:
        pytest.fail(f"Invalid JSON: {out}")

    # search for package with TOS plugin disabled
    monkeypatch.setenv("CONDA_NO_PLUINS", "true")
    reset_context()
    assert not context.no_plugins
    out, _, code = conda_cli("search", "small-executable", "--json")
    assert not code

    try:
        plugin_disabled = json.loads(out)
    except json.JSONDecodeError:
        pytest.fail(f"Invalid JSON: {out}")

    assert plugin_enabled == plugin_disabled


def test_location_flags_ordering_fix() -> None:
    """Test that location flags are only available on subcommands, not main parser.

    This test ensures that GitHub issue #239 is fixed, where
    'conda tos --site accept' would incorrectly write to user location
    instead of failing with unrecognized argument.
    """
    parser = argparse.ArgumentParser()
    configure_parser(parser)

    # Test that location flags work correctly on subcommands
    args = parser.parse_args(["accept", "--user"])
    assert args.tos_root == USER_TOS_ROOT

    # Test that location flags are NOT available on main parser
    # (should raise SystemExit)
    with pytest.raises(SystemExit):
        parser.parse_args(["--user", "accept"])

    with pytest.raises(SystemExit):
        parser.parse_args(["--site", "accept"])

    with pytest.raises(SystemExit):
        parser.parse_args(["--system", "accept"])


@pytest.mark.parametrize(
    ("name", "path"),
    (
        ("related", "/pkgs/related/linux-64/repodata.json"),
        ("related", "/pkgs/related/noarch/repodata_shards.msgpack.zst"),
        ("related", "/pkgs/related/noarch/shards/abc.msgpack.zst"),
        ("related", "/pkgs/related/linux-64/example-1-0.conda"),
        ("related", "/t/synthetic-token/pkgs/related/noarch/repodata.json"),
        ("related%3Atest", "/pkgs/related%3Atest/noarch/repodata.json"),
        ("related%20test", "/pkgs/related%20test/noarch/repodata.json"),
        ("related%2Ftest", "/pkgs/related%2Ftest/noarch/repodata.json"),
    ),
)
@pytest.mark.usefixtures("mock_search_path")
def test_request_headers_include_unconfigured_channel(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    tos_metadata: RemoteToSMetadata,
    name: str,
    path: str,
) -> None:
    monkeypatch.setattr(plugin, "DEFAULT_TOS_ROOT", tmp_path)
    channel = Channel(f"https://repo.anaconda.com/pkgs/{name}")
    write_metadata(tmp_path, channel, tos_metadata, tos_accepted=True)
    for url in (
        "https://repo.anaconda.com/pkgs/unrelated",
        "https://repo.anaconda.com/pkgs",
        "https://repo.anaconda.com:8443/pkgs/related",
    ):
        write_metadata(tmp_path, url, tos_metadata, tos_accepted=True)

    headers = list(conda_request_headers("repo.anaconda.com", path))
    assert headers[0].value.startswith(
        f"{channel}={int(tos_metadata.version.timestamp())}=accepted="
    )
    assert "synthetic-token" not in headers[0].value
    assert "unrelated" not in headers[0].value
    assert ":8443" not in headers[0].value
    assert "https://repo.anaconda.com/pkgs=" not in headers[0].value
    assert (
        next(
            conda_request_headers(
                "repo.anaconda.com", "/pkgs/related-extra/noarch/repodata.json"
            )
        ).value
        == ""
    )


@pytest.mark.usefixtures("mock_search_path")
def test_request_headers_follow_decisions_without_manual_cache_clearing(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    tos_metadata: RemoteToSMetadata,
) -> None:
    monkeypatch.setattr(plugin, "DEFAULT_TOS_ROOT", tmp_path)
    channel = Channel("https://repo.anaconda.com/pkgs/related")
    url = f"{channel}/noarch/repodata.json"
    session = get_session(url)
    context.plugin_manager.get_cached_request_headers.cache_clear()

    assert (
        session.prepare_request(Request("GET", url)).headers["Anaconda-ToS-Accept"]
        == ""
    )
    write_metadata(tmp_path, channel, tos_metadata, tos_accepted=True)
    assert (
        "=accepted="
        in session.prepare_request(Request("GET", url)).headers["Anaconda-ToS-Accept"]
    )
    write_metadata(tmp_path, channel, tos_metadata, tos_accepted=False)
    assert (
        "=rejected="
        in session.prepare_request(Request("GET", url)).headers["Anaconda-ToS-Accept"]
    )
    assert list(clean_tos(tmp_path))
    assert (
        session.prepare_request(Request("GET", url)).headers["Anaconda-ToS-Accept"]
        == ""
    )


def test_fetch_hook_is_optional_on_older_conda(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delattr(plugin.types, "CondaPreChannelFetch", raising=False)
    assert list(plugin.conda_pre_channel_fetches()) == []


@pytest.mark.skipif(
    not hasattr(plugin.types, "CondaPreChannelFetch"),
    reason="conda does not expose the channel fetch hook",
)
@pytest.mark.parametrize("auto_accept", (False, True))
@pytest.mark.usefixtures("mock_search_path")
def test_fetch_checks_unconfigured_channel(
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    tmp_path: Path,
    tos_channel: Channel,
    sample_channel: Channel,
    auto_accept: bool,
) -> None:
    monkeypatch.setattr(plugin, "DEFAULT_TOS_ROOT", tmp_path)
    monkeypatch.setattr(render, "IS_INTERACTIVE", False)
    monkeypatch.setenv("CONDA_PLUGINS_AUTO_ACCEPT_TOS", str(auto_accept).lower())
    reset_context()
    mocker.patch(
        "conda.base.context.Context.channels",
        new_callable=mocker.PropertyMock,
        return_value=(sample_channel,),
    )

    if auto_accept:
        context.plugin_manager.invoke_pre_channel_fetch(tos_channel)
        assert get_local_metadata(
            tos_channel, extend_search_path=[tmp_path]
        ).metadata.tos_accepted
        reject_tos(tos_channel, tos_root=tmp_path, cache_timeout=None)
        with pytest.raises(CondaToSRejectedError):
            context.plugin_manager.invoke_pre_channel_fetch(tos_channel)
    else:
        with pytest.raises(CondaToSNonInteractiveError):
            context.plugin_manager.invoke_pre_channel_fetch(tos_channel)
        with pytest.raises(CondaToSMissingError):
            get_local_metadata(tos_channel, extend_search_path=[tmp_path])


@pytest.mark.skipif(
    not hasattr(plugin.types, "CondaPreChannelFetch"),
    reason="conda does not expose the channel fetch hook",
)
@pytest.mark.usefixtures("mock_search_path")
def test_fetch_does_not_allow_unavailable_terms(
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    tmp_path: Path,
    tos_channel: Channel,
    tos_metadata: RemoteToSMetadata,
) -> None:
    monkeypatch.setattr(plugin, "DEFAULT_TOS_ROOT", tmp_path)
    monkeypatch.setenv("CONDA_PLUGINS_AUTO_ACCEPT_TOS", "true")
    reset_context()
    write_metadata(tmp_path, tos_channel, tos_metadata, tos_accepted=True)
    mocker.patch(
        "conda_anaconda_tos.remote.get_endpoint",
        side_effect=CondaToSUnavailableError(tos_channel),
    )

    with pytest.raises(CondaToSUnavailableError):
        context.plugin_manager.invoke_pre_channel_fetch(tos_channel)


@pytest.mark.skipif(
    not hasattr(plugin.types, "CondaPreChannelFetch"),
    reason="conda does not expose the channel fetch hook",
)
@pytest.mark.parametrize("require_explicit_consent", (False, True))
@pytest.mark.usefixtures("mock_search_path")
def test_related_metadata_waits_for_consent(
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    tmp_path: Path,
    tos_metadata: RemoteToSMetadata,
    require_explicit_consent: bool,
) -> None:
    tos_root = tmp_path / "tos"
    monkeypatch.setattr(plugin, "DEFAULT_TOS_ROOT", tos_root)
    monkeypatch.setenv("CONDA_PLUGINS_AUTO_ACCEPT_TOS", "true")
    reset_context()
    related = tmp_path / "related"
    (related / "noarch").mkdir(parents=True)
    (related / "terms.json").write_text(tos_metadata.model_dump_json())
    (related / "noarch" / "repodata.json").write_text(
        json.dumps(
            {"info": {"subdir": "noarch"}, "packages": {}, "packages.conda": {}}
        ),
    )
    tos_channel = Channel(related.as_uri())
    head = tmp_path / "head"
    (head / "noarch").mkdir(parents=True)
    (head / "noarch" / "repodata.json").write_text(
        json.dumps(
            {
                "info": {
                    "subdir": "noarch",
                    "channel_relations": {"base": "../related"},
                },
                "packages": {},
                "packages.conda": {},
            },
        ),
    )
    mocker.patch(
        "conda.base.context.Context.channels",
        new_callable=mocker.PropertyMock,
        return_value=(head.as_uri(),),
    )
    loads = mocker.spy(SubdirData, "load")

    def check_consent(channel: Channel) -> None:
        result = collect_channel_consent(
            channel,
            tos_root=tos_root,
            cache_timeout=0,
        )
        if "required" in result.values():
            raise CondaToSNonInteractiveError(channel)

    if require_explicit_consent:
        with pytest.raises(CondaToSNonInteractiveError):
            channel_index.resolve_channels(
                [head.as_uri()],
                ["noarch"],
                before_fetch=check_consent,
                use_shards=False,
            )
        assert loads.call_args_list
        assert all(
            call.args[0].channel.base_url == head.as_uri()
            for call in loads.call_args_list
        )
        with pytest.raises(CondaToSMissingError):
            get_local_metadata(tos_channel, extend_search_path=[tos_root])
    else:
        channels = channel_index.resolve_channels(
            [head.as_uri()],
            ["noarch"],
            use_shards=False,
        )
        assert {channel.base_url for channel in channels} == {
            head.as_uri(),
            tos_channel.base_url,
        }
        assert get_local_metadata(
            tos_channel,
            extend_search_path=[tos_root],
        ).metadata.tos_accepted
