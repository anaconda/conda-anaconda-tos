# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""High-level API functions for interacting with a channel's Terms of Service."""

from __future__ import annotations

import json
import os
import shutil
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from conda.auxlib.type_coercion import boolify
from conda.models.channel import Channel

from . import APP_VERSION
from .exceptions import CondaToSBackupError, CondaToSMissingError
from .local import get_local_metadata, get_local_metadatas, write_metadata
from .models import BackupFileInfo, LocalPair, RemotePair
from .path import (
    TOS_BACKUP_DIR,
    get_all_channel_paths,
    get_cache_paths,
    get_location_hash,
    get_path,
    get_search_path,
    is_temporary_location,
)
from .remote import get_remote_metadata

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from typing import Final
#: Boolean CI environment variables (checked with boolify)
#: Sources: Official CI platform documentation and community knowledge base
CI_BOOLEAN_VARS: Final = (
    "APPVEYOR",  # AppVeyor CI (https://www.appveyor.com/docs/environment-variables/)
    "BITRISE_IO",  # Bitrise (https://devcenter.bitrise.io/en/references/available-environment-variables.html)
    "BUDDY",  # Buddy CI/CD (https://buddy.works/docs/pipelines/environment-variables)
    "BUILDKITE",  # Buildkite (https://buildkite.com/docs/pipelines/environment-variables)
    "CI",  # Generic CI indicator (many platforms)
    "CIRCLECI",  # CircleCI (https://circleci.com/docs/variables/#built-in-environment-variables)
    "CIRRUS_CI",  # Cirrus CI (https://cirrus-ci.org/guide/environment-variables/)
    "CONCOURSE_CI",  # Concourse CI (https://concourse-ci.org/implementing-resource-types.html#environment)
    "DRONE",  # Drone CI (https://docs.drone.io/pipeline/environment/reference/)
    "GITHUB_ACTIONS",  # GitHub Actions (https://docs.github.com/en/actions/learn-github-actions/variables#default-environment-variables)
    "GITLAB_CI",  # GitLab CI/CD (https://docs.gitlab.com/ee/ci/variables/predefined_variables.html)
    "SAIL_CI",  # Sail CI
    "SEMAPHORE",  # Semaphore CI (https://docs.semaphoreci.com/ci-cd-environment/environment-variables/)
    "TF_BUILD",  # Azure DevOps (Team Foundation) (https://docs.microsoft.com/en-us/azure/devops/pipelines/build/variables)
    "TRAVIS",  # Travis CI (https://docs.travis-ci.com/user/environment-variables/#default-environment-variables)
    "WERCKER",  # Wercker (deprecated)
    "WOODPECKER_CI",  # Woodpecker CI (https://woodpecker-ci.org/docs/usage/environment)
)

#: Presence-based CI environment variables (checked for existence)
#: Sources: Official CI platform documentation
CI_PRESENCE_VARS: Final = (
    "BAMBOO_BUILDKEY",  # Atlassian Bamboo (https://confluence.atlassian.com/bamboo/bamboo-variables-289277087.html)
    "CODEBUILD_BUILD_ID",  # AWS CodeBuild (https://docs.aws.amazon.com/codebuild/latest/userguide/build-env-ref-env-vars.html)
    "HEROKU_TEST_RUN_ID",  # Heroku CI (https://devcenter.heroku.com/articles/heroku-ci#environment-variables)
    "JENKINS_URL",  # Jenkins (https://www.jenkins.io/doc/book/pipeline/jenkinsfile/#using-environment-variables)
    "TEAMCITY_VERSION",  # JetBrains TeamCity (https://www.jetbrains.com/help/teamcity/predefined-build-parameters.html)
)
#: Container indicators for cgroup detection
#: Reference: https://github.com/containers/podman/issues/3586,
#: Docker/containerd documentation
CONTAINER_INDICATORS: Final = (
    "containerd",  # containerd runtime
    "docker",  # Docker containers
    "kubepods",  # Kubernetes pods (https://kubernetes.io/docs/tasks/administer-cluster/migrating-from-dockershim/find-out-runtime-you-use/)
    "lxc",  # Linux Containers
    "podman",  # Podman containers
)

#: Partial CI environment variables (used with container detection)
#: These variables may be present in containerized CI environments that don't
#: set full CI variables
PARTIAL_CI_VARS: Final = (
    "AZURE_HTTP_USER_AGENT",  # Azure DevOps user agent
    "BUILD_ID",  # Generic build identifier (Jenkins, etc.)
    "BUILD_NUMBER",  # Generic build number (Jenkins, etc.)
    "BUILD_URL",  # Generic build URL (Jenkins, etc.)
    "BUILDKITE_BUILD_ID",  # Buildkite build identifier
    "CIRCLE_BUILD_NUM",  # CircleCI build number
    "CIRCLE_PROJECT_REPONAME",  # CircleCI repository name
    "GITHUB_JOB",  # GitHub Actions job name
    "GITHUB_REPOSITORY",  # GitHub repository name
    "GITHUB_WORKFLOW",  # GitHub Actions workflow name
    "GITLAB_PROJECT_ID",  # GitLab project identifier
    "GITLAB_USER_ID",  # GitLab user identifier
    "JOB_NAME",  # Generic job name (Jenkins, etc.)
    "RUNNER_ARCH",  # GitHub Actions runner architecture
    "RUNNER_OS",  # GitHub Actions runner OS
    "WORKSPACE",  # Generic workspace path (Jenkins, etc.)
)


def _in_ci_container() -> bool:
    """Detect if running in a containerized CI environment.

    This function combines container detection with partial CI environment variables
    to address cases where CI systems run jobs in containers but don't set complete
    CI environment variables (see GitHub issue #232). This is a workaround for
    https://github.com/anaconda/conda-anaconda-tos/issues/232.

    Returns:
        bool: True if both container indicators and partial CI variables are present

    """
    # Check documented container indicators
    container_checks = [
        os.getpid() == 1,  # Process ID 1 (init process in containers)
        bool(os.environ.get("CONTAINER")),  # Generic container environment variable
    ]

    # Check cgroup for container runtime identifiers (Docker official method)
    # Reference: https://docs.docker.com/engine/containers/runmetrics/#find-the-cgroup-for-a-given-container
    try:
        with Path("/proc/self/cgroup").open() as f:
            cgroup_content = f.read()
            # Container runtime signatures in cgroups (documented by Docker):
            # - "docker": Docker containers
            # - "containerd": containerd runtime
            # - "kubepods": Kubernetes pods
            # - "lxc": Linux Containers
            # - "podman": Podman containers
            if any(indicator in cgroup_content for indicator in CONTAINER_INDICATORS):
                container_checks.append(True)
    except OSError:
        # Ignore errors (e.g., on non-Linux systems or restricted access)
        pass

    # Return True only if we detect container AND partial CI indicators
    # This prevents false positives from containers without CI context
    return any(container_checks) and any(os.getenv(var) for var in PARTIAL_CI_VARS)


def _is_ci() -> bool:
    """Determine if running in a CI environment.

    This function uses a multi-layered approach to detect CI environments:
    1. First checks if any CI variables are explicitly set to false
       (respects user override)
    2. Then checks boolean CI variables for true values
    3. Finally checks presence-based variables and container environments

    Returns:
        bool: True if running in a detected CI environment

    """
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
    return any(os.getenv(var) for var in CI_PRESENCE_VARS) or _in_ci_container()


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


def backup_tos_configs() -> Path:
    """Backup ToS configuration files from all search path locations.

    Returns:
        Path to the created backup directory

    Raises:
        CondaToSBackupError: If backup directory cannot be created or files
            cannot be copied.

    """
    backup_timestamp = datetime.now(tz=timezone.utc)
    timestamped_backup_dir = TOS_BACKUP_DIR / (
        f"backup_{int(backup_timestamp.timestamp())}"
    )

    # Create backup directory
    try:
        timestamped_backup_dir.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as e:
        raise CondaToSBackupError("create", timestamped_backup_dir, str(e)) from e

    # Collect ToS files with location metadata from all search path locations
    file_info: list[BackupFileInfo] = []

    for search_path in get_search_path():
        for tos_file in search_path.glob("*/*.json"):
            if tos_file.is_file():
                file_info.append(
                    BackupFileInfo(
                        file_path=tos_file,
                        source_location=str(search_path),
                        is_temporary=is_temporary_location(search_path),
                    )
                )

    if file_info:
        # Create backup structure preserving source information
        backup_configs_dir = timestamped_backup_dir / "configs"
        try:
            backup_configs_dir.mkdir(exist_ok=True)
        except (PermissionError, OSError) as e:
            raise CondaToSBackupError(
                "create configs directory", backup_configs_dir, str(e)
            ) from e

        for info in file_info:
            source_location = Path(info.source_location).expanduser().resolve()

            try:
                tos_file_resolved = info.file_path.resolve()
                # Create a path structure that preserves source location info
                rel_path = tos_file_resolved.relative_to(source_location)
                # Include source identifier in backup path
                source_hash = get_location_hash(source_location)
                backup_file = backup_configs_dir / source_hash / rel_path
                backup_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(info.file_path, backup_file)
            except (ValueError, PermissionError, OSError):
                # File issues, skip but continue with other files
                continue

    # Create metadata file
    metadata = {
        "timestamp": backup_timestamp.isoformat(),
        "backup_type": "comprehensive",
        "files_count": len(file_info),
        "source_locations": list({info.source_location for info in file_info}),
        "temporary_locations": list(
            {info.source_location for info in file_info if info.is_temporary}
        ),
        "persistent_locations": list(
            {info.source_location for info in file_info if not info.is_temporary}
        ),
        "files": [
            {
                "path": str(info.file_path),
                "source_location": info.source_location,
                "is_temporary": info.is_temporary,
            }
            for info in file_info
        ],
        "version": APP_VERSION,
    }

    metadata_file = timestamped_backup_dir / "metadata.json"
    try:
        with metadata_file.open("w") as f:
            json.dump(metadata, f, indent=2)
    except (PermissionError, OSError) as e:
        raise CondaToSBackupError("write metadata", metadata_file, str(e)) from e

    return timestamped_backup_dir


def restore_tos_configs(
    timeout_hours: float = 1.0,
) -> tuple[bool, list[Path]]:
    """Restore ToS configuration files from recent backup to exact original locations.

    Args:
        timeout_hours: Timeout in hours for considering backups recent

    Returns:
        - bool: True if any restore was performed, False otherwise
        - list[Path]: List of successfully restored files

    Raises:
        FileNotFoundError: If the backup directory does not exist

    """
    backup_dir = TOS_BACKUP_DIR

    if not backup_dir.exists():
        raise FileNotFoundError(f"Backup directory does not exist: {backup_dir}")

    # Find recent backups within timeout period
    timeout_cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=timeout_hours)
    recent_backups = []

    for individual_backup_dir in backup_dir.iterdir():
        if (
            not individual_backup_dir.is_dir()
            or not individual_backup_dir.name.startswith("backup_")
        ):
            continue

        metadata_file = individual_backup_dir / "metadata.json"
        if not metadata_file.exists():
            continue

        try:
            with metadata_file.open() as f:
                metadata = json.load(f)

            backup_time = datetime.fromisoformat(metadata["timestamp"])
            if backup_time >= timeout_cutoff:
                recent_backups.append((backup_time, individual_backup_dir, metadata))
        except (json.JSONDecodeError, KeyError, ValueError):
            # Invalid metadata, skip this backup
            continue

    if not recent_backups:
        return False, []

    # Use the most recent backup
    _, latest_backup_dir, metadata = max(recent_backups, key=lambda x: x[0])

    # Restore files using enhanced metadata for exact location restoration
    configs_dir = latest_backup_dir / "configs"
    restored_files = []

    if (
        configs_dir.exists()
        and metadata.get("version") is not None
        and "files" in metadata
    ):
        restored_files = _restore_with_metadata(configs_dir, metadata)

    return bool(restored_files), restored_files


def _restore_with_metadata(configs_dir: Path, metadata: dict) -> list[Path]:
    """Restore files using enhanced metadata to their exact original locations."""
    restored_files = []

    # Group files by their original source locations
    files_by_source: dict[str, list[dict]] = defaultdict(list)
    for file_info in metadata.get("files", []):
        files_by_source[file_info["source_location"]].append(file_info)

    for source_location in files_by_source:
        # Always try to restore to the exact original location
        try:
            original_path = get_path(source_location)
            # Test if we can write to the original location
            original_path.mkdir(parents=True, exist_ok=True)
            test_file = original_path / ".write_test"
            test_file.touch()
            test_file.unlink()

            # Original location is writable, restore files there
            source_hash = get_location_hash(source_location)
            source_backup_dir = configs_dir / source_hash

            if source_backup_dir.exists():
                for backup_file in source_backup_dir.rglob("*"):
                    if backup_file.is_file():
                        try:
                            # Calculate relative path from source backup dir
                            rel_path = backup_file.relative_to(source_backup_dir)
                            target_file = original_path / rel_path

                            # Create target directory if needed
                            target_file.parent.mkdir(parents=True, exist_ok=True)

                            # Restore file to exact original location
                            shutil.copy2(backup_file, target_file)
                            restored_files.append(target_file)
                        except (PermissionError, OSError, ValueError):
                            # Skip individual files that cannot be restored
                            continue

        except (PermissionError, OSError):
            # Cannot write to original location - skip all files from this source
            # This is intentional: better to require re-consent than restore to
            # wrong location
            continue

    return restored_files


def clean_backup_dir(older_than_hours: float = 24.0) -> Iterator[Path]:
    """Clean old backup files from backup directory.

    Args:
        older_than_hours: Remove backups older than this many hours

    Yields:
        Path: Paths of removed backup directories

    """
    backup_dir = TOS_BACKUP_DIR

    if not backup_dir.exists():
        return

    cutoff_time = datetime.now(tz=timezone.utc) - timedelta(hours=older_than_hours)

    for individual_backup_dir in backup_dir.iterdir():
        if (
            not individual_backup_dir.is_dir()
            or not individual_backup_dir.name.startswith("backup_")
        ):
            continue

        try:
            timestamp_str = individual_backup_dir.name.replace("backup_", "")
            backup_time = datetime.fromtimestamp(float(timestamp_str), tz=timezone.utc)

            if backup_time < cutoff_time:
                shutil.rmtree(individual_backup_dir)
                yield individual_backup_dir
        except (ValueError, OSError):
            # Invalid timestamp or removal failed, skip
            continue
