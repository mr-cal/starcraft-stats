"""Tests for Library version logic."""

import pytest
from packaging.version import Version
from starcraft_stats.library import Library


@pytest.fixture
def library():
    """A Library with a known set of versions, bypassing subprocess calls."""
    lib = Library.__new__(Library)
    lib.name = "craft-cli"
    lib.versions = [
        Version("1.0.0"),
        Version("1.0.1"),
        Version("1.0.2"),
        Version("1.1.0"),
        Version("1.1.1"),
        Version("2.0.0"),
    ]
    return lib


class TestLibrary:
    def test_latest_returns_highest_version(self, library):
        assert library.latest == Version("2.0.0")

    def test_latest_in_series_returns_highest_patch(self, library):
        assert library.latest_in_series(Version("1.0.0")) == Version("1.0.2")

    def test_latest_in_series_for_different_minor(self, library):
        assert library.latest_in_series(Version("1.1.0")) == Version("1.1.1")

    def test_latest_in_series_for_major_only_version(self, library):
        assert library.latest_in_series(Version("2.0.0")) == Version("2.0.0")

    def test_is_latest_patch_true_for_highest_patch(self, library):
        assert library.is_latest_patch(Version("1.0.2")) is True

    def test_is_latest_patch_false_when_newer_patch_exists(self, library):
        assert library.is_latest_patch(Version("1.0.1")) is False

    def test_is_latest_patch_true_when_only_version_in_series(self, library):
        assert library.is_latest_patch(Version("2.0.0")) is True


class TestParseVersionsOutput:
    def test_returns_versions_from_pip_error_line(self):
        lines = [
            "ERROR: Could not find a version that satisfies the requirement craft-cli==1111111",
            "ERROR: No matching distribution found for craft-cli==1111111 from versions: 1.0.0, 1.0.1, 2.0.0)",
        ]
        result = Library._parse_versions_output(lines)
        assert result == [Version("1.0.0"), Version("1.0.1"), Version("2.0.0")]

    def test_returns_empty_list_when_no_versions(self):
        lines = ["ERROR: No matching distribution found from versions: none)"]
        result = Library._parse_versions_output(lines)
        assert result == []

    def test_returns_none_when_anchor_not_found(self):
        lines = ["some unrelated output", "another line"]
        result = Library._parse_versions_output(lines)
        assert result is None

    def test_returns_none_for_empty_output(self):
        assert Library._parse_versions_output([]) is None
