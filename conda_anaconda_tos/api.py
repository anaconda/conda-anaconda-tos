# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""High-level API functions for interacting with a channel's Terms of Service."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from conda.auxlib.type_coercion import boolify
from conda.models.channel import Channel

from .exceptions import CondaToSMissingError
from .local import get_local_metadata, get_local_metadatas, write_metadata
from .models import LocalPair, RemotePair
from .path import get_all_channel_paths, get_cache_paths
from .remote import get_remote_metadata

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path
    from typing import Final


#: Boolean CI environment variables (checked with boolify)
CI_BOOLEAN_VARS: Final = (
    "APPVEYOR",  # AppVeyor CI
    "BITRISE_IO",  # Bitrise
    "BUDDY",  # Buddy CI/CD
    "BUILDKITE",  # Buildkite
    "CI",  # Generic CI indicator (many platforms)
    "CIRCLECI",  # CircleCI
    "CIRRUS_CI",  # Cirrus CI
    "CONCOURSE_CI",  # Concourse CI
    "DRONE",  # Drone CI
    "GITHUB_ACTIONS",  # GitHub Actions
    "GITLAB_CI",  # GitLab CI/CD
    "SAIL_CI",  # Sail CI
    "SEMAPHORE",  # Semaphore CI
    "TF_BUILD",  # Azure DevOps (Team Foundation)
    "TRAVIS",  # Travis CI
    "WERCKER",  # Wercker (deprecated)
    "WOODPECKER_CI",  # Woodpecker CI
)

#: Presence-based CI environment variables (checked for existence)
CI_PRESENCE_VARS: Final = (
    "BAMBOO_BUILDKEY",  # Atlassian Bamboo
    "CODEBUILD_BUILD_ID",  # AWS CodeBuild
    "HEROKU_TEST_RUN_ID",  # Heroku CI
    "JENKINS_URL",  # Jenkins
    "TEAMCITY_VERSION",  # JetBrains TeamCity
)


def _is_ci() -> bool:
    """Determine if running in a CI environment."""
    # Check all boolean CI variables for explicit false values first
    # If any CI variable is explicitly set to false, respect that
    for var_value in map(os.getenv, CI_BOOLEAN_VARS):
        if var_value and not boolify(var_value):
            return False

    # Check boolean CI environment variables for true values
    for var_value in map(os.getenv, CI_BOOLEAN_VARS):
        if boolify(var_value):
            return True

    # Check presence-based CI environment variables
    return any(os.getenv(var) for var in CI_PRESENCE_VARS)


#: Whether the current environment is a CI environment
CI: Final = _is_ci()

#: Whether the current environment is a Jupyter environment
JUPYTER: Final = os.getenv("JPY_SESSION_NAME") and os.getenv("JPY_PARENT_PID")


def get_channels(*channels: str | Channel) -> Iterable[Channel]:
    """Yield all unique channels from the given channels."""
    # expand every multichannel into its individual channels
    # and remove any duplicates
    seen: set[Channel] = set()
    for multichannel in map(Channel, channels):
        for channel in map(Channel, multichannel.urls()):
            channel = Channel(channel.base_url)
            if channel not in seen:
                yield channel
                seen.add(channel)


def get_one_tos(
    channel: str | Channel,
    *,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int | float | None,
) -> LocalPair | RemotePair:
    """Get the Terms of Service metadata for the given channel."""
    # fetch remote metadata
    remote_metadata = remote_exc = None
    try:
        remote_metadata = get_remote_metadata(channel, cache_timeout=cache_timeout)
    except CondaToSMissingError as exc:
        # CondaToSMissingError: no remote metadata
        remote_exc = exc

    # fetch local metadata
    try:
        local_pair = get_local_metadata(channel, extend_search_path=[tos_root])
    except CondaToSMissingError as exc:
        # CondaToSMissingError: no local metadata
        if remote_exc:
            raise remote_exc from exc
        # no local ToS metadata
        return RemotePair(metadata=remote_metadata)
    else:
        # return local metadata, include remote metadata if newer
        if not remote_metadata or local_pair.metadata >= remote_metadata:
            return local_pair
        return LocalPair(
            metadata=local_pair.metadata,
            path=local_pair.path,
            remote=remote_metadata,
        )


def get_stored_tos(
    *,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int | float | None,
) -> Iterator[tuple[Channel, LocalPair]]:
    """Yield metadata of all stored Terms of Service."""
    for channel, local_pair in get_local_metadatas(extend_search_path=[tos_root]):
        try:
            remote_metadata = get_remote_metadata(channel, cache_timeout=cache_timeout)
        except CondaToSMissingError:
            # CondaToSMissingError: no remote metadata
            continue

        # yield local metadata, include remote metadata if newer
        if local_pair.metadata >= remote_metadata:
            yield channel, local_pair
        else:
            yield (
                channel,
                LocalPair(
                    metadata=local_pair.metadata,
                    path=local_pair.path,
                    remote=remote_metadata,
                ),
            )


def accept_tos(
    channel: str | Channel,
    *,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int | float | None,
) -> LocalPair:
    """Accept the Terms of Service for the given channel."""
    pair = get_one_tos(
        channel,
        tos_root=tos_root,
        cache_timeout=cache_timeout,
    )
    metadata = pair.remote or pair.metadata
    return write_metadata(tos_root, channel, metadata, tos_accepted=True)


def reject_tos(
    channel: str | Channel,
    *,
    tos_root: str | os.PathLike[str] | Path,
    cache_timeout: int | float | None,
) -> LocalPair:
    """Reject the Terms of Service for the given channel."""
    pair = get_one_tos(
        channel,
        tos_root=tos_root,
        cache_timeout=cache_timeout,
    )
    metadata = pair.remote or pair.metadata
    return write_metadata(tos_root, channel, metadata, tos_accepted=False)


def get_all_tos(
    *channels: str | Channel,
    tos_root: str | os.PathLike | Path,
    cache_timeout: int | float | None,
) -> Iterator[tuple[Channel, LocalPair | RemotePair | None]]:
    """List all channels and whether their Terms of Service have been accepted."""
    # list all active channels
    seen: set[Channel] = set()
    for channel in get_channels(*channels):
        try:
            yield (
                channel,
                get_one_tos(channel, tos_root=tos_root, cache_timeout=cache_timeout),
            )
        except CondaToSMissingError:
            yield channel, None
        seen.add(channel)

    # list all other channels whose Terms of Service have been accepted/rejected
    for channel, metadata_pair in get_stored_tos(
        tos_root=tos_root,
        cache_timeout=cache_timeout,
    ):
        if channel not in seen:
            yield channel, metadata_pair
            seen.add(channel)


def clean_cache() -> Iterator[Path]:
    """Clean all metadata cache files."""
    for path in get_cache_paths():
        try:
            path.unlink()
        except (PermissionError, FileNotFoundError, IsADirectoryError):
            # PermissionError: no permission to delete the file
            # FileNotFoundError: the file doesn't exist
            # IsADirectoryError: the path is a directory
            pass
        else:
            yield path


def clean_tos(tos_root: str | os.PathLike[str] | Path) -> Iterator[Path]:
    """Clean all metadata directories."""
    for path in get_all_channel_paths(extend_search_path=[tos_root]):
        try:
            path.unlink()
        except (PermissionError, FileNotFoundError, IsADirectoryError):
            # PermissionError: no permission to delete the file
            # FileNotFoundError: the file doesn't exist
            # IsADirectoryError: the path is a directory
            pass
        else:
            yield path
