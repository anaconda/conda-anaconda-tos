# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from conda.auxlib.type_coercion import BOOLISH_FALSE, BOOLISH_TRUE
from conda.base.context import context
from conda.models.channel import Channel

from conda_anaconda_tos import api
from conda_anaconda_tos.api import (
    CI_BOOLEAN_VARS,
    CI_PRESENCE_VARS,
    _is_ci,
    _restore_with_metadata,
    accept_tos,
    backup_tos_configs,
    clean_backup_dir,
    get_all_tos,
    get_channels,
    get_one_tos,
    get_stored_tos,
    reject_tos,
    restore_tos_configs,
)
from conda_anaconda_tos.exceptions import CondaToSMissingError
from conda_anaconda_tos.models import (
    LocalPair,
    LocalToSMetadata,
    RemotePair,
    RemoteToSMetadata,
)

if TYPE_CHECKING:
    from typing import Callable

    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture


def test_get_channels() -> None:
    defaults = set(map(Channel, context.default_channels))
    assert set(get_channels("defaults")) == defaults

    conda_forge = {Channel("conda-forge")}
    assert set(get_channels("conda-forge")) == conda_forge

    assert set(get_channels("defaults", "conda-forge")) == defaults | conda_forge


@pytest.fixture(scope="session")
def remote_metadata_pair() -> RemotePair:
    return RemotePair(
        metadata=RemoteToSMetadata(
            version=datetime(2024, 11, 1, tzinfo=timezone.utc),
            text="new Terms of Service",
            support="support.com",
        ),
    )


@pytest.fixture(scope="session")
def local_metadata_pair(
    remote_metadata_pair: RemotePair,
    sample_channel: Channel,
) -> LocalPair:
    return LocalPair(
        metadata=LocalToSMetadata(
            **remote_metadata_pair.metadata.model_dump(),
            base_url=sample_channel.base_url,
            tos_accepted=True,
            acceptance_timestamp=datetime.now(tz=timezone.utc),
        ),
        path=uuid4().hex,
    )


@pytest.fixture(scope="session")
def old_metadata_pair(
    sample_channel: Channel,
    remote_metadata_pair: RemotePair,
) -> LocalPair:
    return LocalPair(
        metadata=LocalToSMetadata(
            version=datetime(2024, 10, 1, tzinfo=timezone.utc),
            text="old Terms of Service",
            support="support.com",
            base_url=sample_channel.base_url,
            tos_accepted=True,
            acceptance_timestamp=datetime.now(tz=timezone.utc),
        ),
        path=uuid4().hex,
        remote=remote_metadata_pair.metadata,
    )


def test_get_one_tos(
    mocker: MockerFixture,
    tmp_path: Path,
    sample_channel: Channel,
    remote_metadata_pair: RemotePair,
    local_metadata_pair: LocalPair,
    old_metadata_pair: LocalPair,
) -> None:
    # mock remote metadata and no local metadata
    mocker.patch(
        "conda_anaconda_tos.api.get_remote_metadata",
        return_value=remote_metadata_pair.metadata,
    )
    mocker.patch(
        "conda_anaconda_tos.api.get_local_metadata",
        side_effect=CondaToSMissingError(sample_channel),
    )
    assert remote_metadata_pair == get_one_tos(
        sample_channel,
        tos_root=tmp_path,
        cache_timeout=None,
    )

    # mock local metadata version matches remote metadata version
    mocker.patch(
        "conda_anaconda_tos.api.get_local_metadata",
        return_value=local_metadata_pair,
    )
    assert local_metadata_pair == get_one_tos(
        sample_channel,
        tos_root=tmp_path,
        cache_timeout=None,
    )

    # mock local metadata version is outdated
    mocker.patch(
        "conda_anaconda_tos.api.get_local_metadata",
        return_value=old_metadata_pair,
    )
    assert old_metadata_pair == get_one_tos(
        sample_channel,
        tos_root=tmp_path,
        cache_timeout=None,
    )

    # mock local metadata exists but remote metadata are missing
    mocker.patch(
        "conda_anaconda_tos.api.get_remote_metadata",
        side_effect=CondaToSMissingError(sample_channel),
    )
    assert old_metadata_pair == get_one_tos(
        sample_channel,
        tos_root=tmp_path,
        cache_timeout=None,
    )


def test_get_stored_tos(
    mocker: MockerFixture,
    tmp_path: Path,
    sample_channel: Channel,
    remote_metadata_pair: RemotePair,
    local_metadata_pair: LocalPair,
    old_metadata_pair: LocalPair,
) -> None:
    # mock no remote metadata
    mocker.patch(
        "conda_anaconda_tos.api.get_local_metadatas",
        return_value=[(sample_channel, local_metadata_pair)],
    )
    mocker.patch(
        "conda_anaconda_tos.api.get_remote_metadata",
        side_effect=CondaToSMissingError(sample_channel),
    )
    assert not list(get_stored_tos(tos_root=tmp_path, cache_timeout=None))

    # mock local metadata version matches remote metadata version
    mocker.patch(
        "conda_anaconda_tos.api.get_remote_metadata",
        return_value=remote_metadata_pair.metadata,
    )
    metadata_pairs = list(get_stored_tos(tos_root=tmp_path, cache_timeout=None))
    assert metadata_pairs == [(sample_channel, local_metadata_pair)]

    # mock local metadata version is outdated
    mocker.patch(
        "conda_anaconda_tos.api.get_local_metadatas",
        return_value=[(sample_channel, old_metadata_pair)],
    )
    metadata_pairs = list(get_stored_tos(tos_root=tmp_path, cache_timeout=None))
    assert metadata_pairs == [(sample_channel, old_metadata_pair)]


def test_ci_detection_with_various_values(monkeypatch: MonkeyPatch) -> None:
    """Test CI detection with various truthy environment variable values."""
    # Clear all CI-related environment variables first
    for var in (*CI_BOOLEAN_VARS, *CI_PRESENCE_VARS):
        monkeypatch.delenv(var, raising=False)

    # truthy values
    for envvar in CI_BOOLEAN_VARS:
        for truthy_value in (*BOOLISH_TRUE, "1"):
            monkeypatch.setenv(envvar, truthy_value)
            assert _is_ci(), f"CI should be detected for {envvar}={truthy_value}"
        monkeypatch.delenv(envvar)

    # falsy values
    for envvar in CI_BOOLEAN_VARS:
        for falsy_value in (*BOOLISH_FALSE, "0"):
            monkeypatch.setenv(envvar, falsy_value)
            assert not _is_ci(), f"CI should not be detected for {envvar}={falsy_value}"
        monkeypatch.delenv(envvar)

    # defined values
    for envvar in CI_PRESENCE_VARS:
        monkeypatch.setenv(envvar, "value")
        assert _is_ci(), f"CI should be detected for {envvar}=value"
        monkeypatch.delenv(envvar)


@pytest.fixture
def test_search_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path]:
    """Create test search paths and mock get_search_path."""
    search_path1 = tmp_path / "search1"
    search_path2 = tmp_path / "search2"
    search_path1.mkdir(parents=True)
    search_path2.mkdir(parents=True)

    # Mock get_search_path to return our test paths
    monkeypatch.setattr(api, "get_search_path", lambda: [search_path1, search_path2])
    return search_path1, search_path2


@pytest.fixture
def mock_backup_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Mock the backup directory."""
    backup_dir = tmp_path / "backups"
    monkeypatch.setattr(api, "TOS_BACKUP_DIR", backup_dir)
    return backup_dir


@pytest.fixture
def mock_temporary_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock temporary location check for testing."""

    def mock_temporary(path: str | Path) -> bool:
        # Only mark search1 as temporary, not search2
        path_str = str(path)
        return path_str.endswith("search1") and "search2" not in path_str

    monkeypatch.setattr(api, "is_temporary_location", mock_temporary)


@pytest.fixture
def test_tos_files(test_search_paths: tuple[Path, Path]) -> list[Path]:
    """Create test ToS files in the search paths."""
    search_path1, search_path2 = test_search_paths
    test_files = []

    # Channel 1 in search_path1 (using timestamp-based filename)
    channel1_dir = search_path1 / "channel1"
    channel1_dir.mkdir()
    channel1_file = channel1_dir / "1704067200.0.json"  # 2024-01-01 timestamp
    channel1_file.write_text(
        '{"version": "2024-01-01T00:00:00Z", "text": "Test ToS 1"}'
    )
    test_files.append(channel1_file)

    # Channel 2 in search_path1
    channel2_dir = search_path1 / "channel2"
    channel2_dir.mkdir()
    channel2_file = channel2_dir / "1704153600.0.json"  # 2024-01-02 timestamp
    channel2_file.write_text(
        '{"version": "2024-01-02T00:00:00Z", "text": "Test ToS 2"}'
    )
    test_files.append(channel2_file)

    # Channel 3 in search_path2
    channel3_dir = search_path2 / "channel3"
    channel3_dir.mkdir()
    channel3_file = channel3_dir / "1704240000.0.json"  # 2024-01-03 timestamp
    channel3_file.write_text(
        '{"version": "2024-01-03T00:00:00Z", "text": "Test ToS 3"}'
    )
    test_files.append(channel3_file)

    return test_files


@pytest.fixture
def backup_test_setup(
    test_tos_files: list[Path],
    mock_backup_dir: Path,
    mock_temporary_check: None,  # noqa: ARG001
) -> tuple[Path, list[Path]]:
    """Complete backup test setup combining all necessary fixtures."""
    return mock_backup_dir.parent, test_tos_files


def test_backup_tos_configs(backup_test_setup: tuple[Path, list[Path]]) -> None:
    """Test backup_tos_configs creates proper backup structure."""
    tmp_path, test_files = backup_test_setup

    # Run backup
    backup_path = backup_tos_configs()

    # Verify backup directory structure
    assert backup_path.exists()
    assert backup_path.is_dir()
    assert backup_path.name.startswith("backup_")

    # Verify metadata file exists
    metadata_file = backup_path / "metadata.json"
    assert metadata_file.exists()

    # Verify metadata content
    with metadata_file.open() as f:
        metadata = json.load(f)

    assert metadata["backup_type"] == "comprehensive"
    assert metadata["version"] == api.APP_VERSION
    assert metadata["files_count"] == 3
    assert len(metadata["source_locations"]) == 2
    assert len(metadata["temporary_locations"]) == 1
    assert len(metadata["persistent_locations"]) == 1
    assert len(metadata["files"]) == 3

    # Verify backup files exist
    configs_dir = backup_path / "configs"
    assert configs_dir.exists()

    # Should have hash-named directories for each source location
    hash_dirs = list(configs_dir.iterdir())
    assert len(hash_dirs) == 2

    # Each hash directory should contain the backed up files
    for hash_dir in hash_dirs:
        assert hash_dir.is_dir()
        json_files = list(hash_dir.rglob("*.json"))
        assert len(json_files) >= 1


@pytest.mark.parametrize(
    "search_paths,expected_files_count,expected_locations",
    [
        ([], 0, 0),  # No search paths
        (["empty"], 0, 0),  # Empty search paths
    ],
    ids=["no_paths", "empty_paths"],
)
def test_backup_tos_configs_no_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    search_paths: list[str],
    expected_files_count: int,
    expected_locations: int,
) -> None:
    """Test backup_tos_configs when no ToS files exist."""
    # Mock search paths
    paths = [tmp_path / path for path in search_paths]
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(api, "get_search_path", lambda: paths)
    monkeypatch.setattr(api, "TOS_BACKUP_DIR", tmp_path / "backups")

    # Run backup
    backup_path = backup_tos_configs()

    # Verify backup was created but with no files
    assert backup_path.exists()
    metadata_file = backup_path / "metadata.json"
    assert metadata_file.exists()

    with metadata_file.open() as f:
        metadata = json.load(f)

    assert metadata["files_count"] == expected_files_count
    assert len(metadata["source_locations"]) == expected_locations


@pytest.mark.parametrize(
    "error_scenario,setup_func,expected_exception,expected_match",
    [
        (
            "no_backup_dir",
            lambda tmp_path: tmp_path / "nonexistent",
            FileNotFoundError,
            "Backup directory does not exist",
        ),
    ],
    ids=["no_backup_dir"],
)
def test_restore_tos_configs_error_scenarios(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error_scenario: str,  # noqa: ARG001
    setup_func: Callable[[Path], Path],
    expected_exception: type[Exception],
    expected_match: str,
) -> None:
    """Test restore_tos_configs error scenarios."""
    backup_dir = setup_func(tmp_path)
    monkeypatch.setattr(api, "TOS_BACKUP_DIR", backup_dir)

    with pytest.raises(expected_exception, match=expected_match):
        restore_tos_configs()


@pytest.mark.parametrize(
    "backup_age_hours,expected_success,expected_files",
    [
        (2, False, []),  # Old backup (2 hours old)
        (
            0.5,
            True,
            None,
        ),  # Recent backup (30 minutes old) - files count checked in test
    ],
    ids=["old_backup", "recent_backup"],
)
def test_restore_tos_configs_by_age(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    backup_test_setup: tuple[Path, list[Path]],
    backup_age_hours: float,
    expected_success: bool,
    expected_files: list[Path] | int | None,
) -> None:
    """Test restore_tos_configs with different backup ages."""
    if expected_files is None and expected_success:
        # For recent backup test, we need the actual backup_test_setup
        tmp_path, test_files = backup_test_setup
        backup_tos_configs()  # Create backup first

        # Remove original files to simulate need for restore
        for test_file in test_files:
            test_file.unlink()
            test_file.parent.rmdir()

        expected_files = 3  # We know we have 3 test files
    else:
        # For old backup test, create minimal setup
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        monkeypatch.setattr(api, "TOS_BACKUP_DIR", backup_dir)

        # Create an old backup
        old_backup_dir = backup_dir / "backup_1234567890"
        old_backup_dir.mkdir()
        metadata = {
            "timestamp": (
                datetime.now(tz=timezone.utc) - timedelta(hours=backup_age_hours)
            ).isoformat(),
            "version": api.APP_VERSION,
            "files": [],
        }
        (old_backup_dir / "metadata.json").write_text(json.dumps(metadata))

    success, restored_files = restore_tos_configs()
    assert success == expected_success

    if isinstance(expected_files, int):
        assert len(restored_files) == expected_files
    else:
        assert restored_files == expected_files


def test_restore_tos_configs_successful_restore(
    backup_test_setup: tuple[Path, list[Path]],
) -> None:
    """Test successful restore from recent backup."""
    tmp_path, test_files = backup_test_setup

    # Create a backup first
    backup_tos_configs()

    # Remove original files to simulate need for restore
    for test_file in test_files:
        test_file.unlink()
        test_file.parent.rmdir()

    # Run restore
    success, restored_files = restore_tos_configs()

    # Verify restore was successful
    assert success
    assert len(restored_files) == 3

    # Verify files were restored to original locations
    for restored_file in restored_files:
        assert restored_file.exists()
        assert restored_file.suffix == ".json"


def test_restore_with_metadata_function(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test the _restore_with_metadata helper function."""
    # Create backup structure
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir(parents=True)

    # Create source hash directory
    source_hash = "12345678"
    hash_dir = configs_dir / source_hash
    hash_dir.mkdir()

    # Create backup file (using timestamp-based filename)
    backup_file = hash_dir / "channel1" / "1704067200.0.json"
    backup_file.parent.mkdir(parents=True)
    backup_file.write_text('{"test": "data"}')

    # Create target directory
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    # Mock get_path to return our target directory
    monkeypatch.setattr(api, "get_path", lambda _path: target_dir)

    # Mock get_location_hash to return our known hash
    monkeypatch.setattr(api, "get_location_hash", lambda _location: source_hash)

    # Create metadata
    metadata = {
        "version": "2.0",
        "files": [
            {
                "path": str(backup_file),
                "source_location": str(target_dir),
                "is_temporary": False,
            }
        ],
    }

    # Run restore
    restored_files = _restore_with_metadata(configs_dir, metadata)

    # Verify restoration
    assert len(restored_files) == 1
    restored_file = target_dir / "channel1" / "1704067200.0.json"
    assert restored_file.exists()
    assert restored_file.read_text() == '{"test": "data"}'


@pytest.mark.parametrize(
    "scenario,cleanup_hours,expected_removed,should_exist_dirs",
    [
        (
            "normal_cleanup",
            24.0,
            1,
            ["recent", "other"],
        ),  # Remove old, keep recent + other
        (
            "aggressive_cleanup",
            0.5,
            2,
            ["other"],
        ),  # Remove both old + recent, keep other
        ("no_cleanup", 72.0, 0, ["old", "recent", "other"]),  # Keep all
    ],
    ids=["normal_cleanup", "aggressive_cleanup", "no_cleanup"],
)
def test_clean_backup_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenario: str,  # noqa: ARG001
    cleanup_hours: float,
    expected_removed: int,
    should_exist_dirs: list[str],
) -> None:
    """Test clean_backup_dir with different scenarios."""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr(api, "TOS_BACKUP_DIR", backup_dir)

    # Create old backup (2 days old)
    old_timestamp = (datetime.now(tz=timezone.utc) - timedelta(days=2)).timestamp()
    old_backup_dir = backup_dir / f"backup_{int(old_timestamp)}"
    old_backup_dir.mkdir()
    (old_backup_dir / "test.txt").write_text("old backup")

    # Create recent backup (1 hour old)
    recent_timestamp = (datetime.now(tz=timezone.utc) - timedelta(hours=1)).timestamp()
    recent_backup_dir = backup_dir / f"backup_{int(recent_timestamp)}"
    recent_backup_dir.mkdir()
    (recent_backup_dir / "test.txt").write_text("recent backup")

    # Create non-backup directory (should always be ignored)
    other_dir = backup_dir / "other_dir"
    other_dir.mkdir()
    (other_dir / "test.txt").write_text("other")

    # Clean backups
    removed_dirs = list(clean_backup_dir(older_than_hours=cleanup_hours))

    # Verify correct number of directories removed
    assert len(removed_dirs) == expected_removed

    # Verify expected directories exist
    dir_map = {
        "old": old_backup_dir,
        "recent": recent_backup_dir,
        "other": other_dir,
    }

    for dir_name in should_exist_dirs:
        assert dir_map[dir_name].exists(), f"{dir_name} directory should exist"

    # Verify removed directories don't exist
    for removed_dir in removed_dirs:
        assert not removed_dir.exists(), (
            f"Removed directory {removed_dir} should not exist"
        )


@pytest.mark.parametrize(
    "backup_dir_exists,expected_removed_count",
    [
        (False, 0),  # No backup directory
        (True, 0),  # Empty backup directory
    ],
    ids=["no_backup_dir", "empty_backup_dir"],
)
def test_clean_backup_dir_edge_cases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    backup_dir_exists: bool,
    expected_removed_count: int,
) -> None:
    """Test clean_backup_dir edge cases."""
    if backup_dir_exists:
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
    else:
        backup_dir = tmp_path / "nonexistent"

    monkeypatch.setattr(api, "TOS_BACKUP_DIR", backup_dir)

    # Should not raise error and return empty iterator
    removed_dirs = list(clean_backup_dir())
    assert len(removed_dirs) == expected_removed_count


def test_accept_tos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the accept_tos function."""
    from datetime import datetime

    # Create mock metadata
    mock_metadata = LocalToSMetadata(
        version=datetime(2024, 1, 1, tzinfo=timezone.utc),
        text="Test ToS text",
        support="test@example.com",
        base_url="https://example.com",
        tos_accepted=False,
        acceptance_timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    mock_pair = LocalPair(metadata=mock_metadata, path=tmp_path / "test.json")

    # Mock get_one_tos to return our test data
    monkeypatch.setattr(api, "get_one_tos", lambda *_args, **_kwargs: mock_pair)

    # Mock write_metadata to capture the call
    written_metadata: list[tuple[object, ...]] = []

    def mock_write_metadata(
        tos_root: object, channel: object, metadata: object, tos_accepted: bool
    ) -> LocalPair:
        written_metadata.append((tos_root, channel, metadata, tos_accepted))
        return LocalPair(metadata=metadata, path=tmp_path / "test.json")

    monkeypatch.setattr(api, "write_metadata", mock_write_metadata)

    # Test accept_tos
    result = accept_tos("test-channel", tos_root=tmp_path, cache_timeout=3600)

    # Verify write_metadata was called with tos_accepted=True
    assert len(written_metadata) == 1
    assert written_metadata[0][3] is True  # tos_accepted=True
    assert isinstance(result, LocalPair)


def test_reject_tos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the reject_tos function."""
    from datetime import datetime

    # Create mock metadata
    mock_metadata = LocalToSMetadata(
        version=datetime(2024, 1, 1, tzinfo=timezone.utc),
        text="Test ToS text",
        support="test@example.com",
        base_url="https://example.com",
        tos_accepted=True,
        acceptance_timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    mock_pair = LocalPair(metadata=mock_metadata, path=tmp_path / "test.json")

    # Mock get_one_tos to return our test data
    monkeypatch.setattr(api, "get_one_tos", lambda *_args, **_kwargs: mock_pair)

    # Mock write_metadata to capture the call
    written_metadata: list[tuple[object, ...]] = []

    def mock_write_metadata(
        tos_root: object, channel: object, metadata: object, tos_accepted: bool
    ) -> LocalPair:
        written_metadata.append((tos_root, channel, metadata, tos_accepted))
        return LocalPair(metadata=metadata, path=tmp_path / "test.json")

    monkeypatch.setattr(api, "write_metadata", mock_write_metadata)

    # Test reject_tos
    result = reject_tos("test-channel", tos_root=tmp_path, cache_timeout=3600)

    # Verify write_metadata was called with tos_accepted=False
    assert len(written_metadata) == 1
    assert written_metadata[0][3] is False  # tos_accepted=False
    assert isinstance(result, LocalPair)


def test_get_all_tos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the get_all_tos function."""
    from datetime import datetime

    # Create test channels
    test_channels = [Channel("test1"), Channel("test2")]

    # Mock get_channels to return our test channels
    monkeypatch.setattr(api, "get_channels", lambda *_args: test_channels)

    # Mock get_one_tos to return different responses
    def mock_get_one_tos(channel: Channel, **_kwargs: object) -> LocalPair | None:
        if channel.name == "test1":
            return LocalPair(
                metadata=LocalToSMetadata(
                    version=datetime(2024, 1, 1, tzinfo=timezone.utc),
                    text="Test ToS text",
                    support="test@example.com",
                    base_url="https://example.com",
                    tos_accepted=True,
                    acceptance_timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
                ),
                path=tmp_path / "test1.json",
            )
        elif channel.name == "test2":
            raise CondaToSMissingError("No ToS found")
        return None

    monkeypatch.setattr(api, "get_one_tos", mock_get_one_tos)

    # Mock get_stored_tos to return additional stored ToS
    stored_channels = [
        (
            Channel("test3"),
            LocalPair(
                metadata=LocalToSMetadata(
                    version=datetime(2024, 1, 2, tzinfo=timezone.utc),
                    text="Test ToS text 3",
                    support="test3@example.com",
                    base_url="https://example.com",
                    tos_accepted=False,
                    acceptance_timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
                ),
                path=tmp_path / "test3.json",
            ),
        )
    ]
    monkeypatch.setattr(api, "get_stored_tos", lambda **_kwargs: stored_channels)

    # Test get_all_tos
    results = list(get_all_tos(tos_root=tmp_path, cache_timeout=3600))

    # Verify results
    assert len(results) == 3

    # test1 should have metadata
    test1_result = next((r for r in results if r[0].name == "test1"), None)
    assert test1_result is not None
    assert isinstance(test1_result[1], LocalPair)

    # test2 should have None (missing ToS)
    test2_result = next((r for r in results if r[0].name == "test2"), None)
    assert test2_result is not None
    assert test2_result[1] is None

    # test3 should be from stored ToS
    test3_result = next((r for r in results if r[0].name == "test3"), None)
    assert test3_result is not None
    assert isinstance(test3_result[1], LocalPair)


def test_container_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test container detection in _is_ci function."""
    # Test case where cgroup file exists and contains container indicators
    mock_cgroup_content = "12:memory:/docker/abc123\n11:cpu:/containerd/xyz789"

    # Mock Path.open to return our test content
    from unittest.mock import mock_open

    mock_file = mock_open(read_data=mock_cgroup_content)

    # We need to mock pathlib.Path.open specifically
    original_path_open = Path.open

    def mock_path_open(self: Path, *args: object, **kwargs: object) -> object:
        if str(self) == "/proc/self/cgroup":
            return mock_file()
        return original_path_open(self, *args, **kwargs)  # type: ignore[call-overload]

    monkeypatch.setattr(Path, "open", mock_path_open)

    # Set no CI environment variables (use tuple concatenation instead of |)
    all_ci_vars = CI_BOOLEAN_VARS + CI_PRESENCE_VARS
    for var in all_ci_vars:
        monkeypatch.delenv(var, raising=False)

    # Should detect container but not CI (returns False since we need both)
    assert _is_ci() is False
