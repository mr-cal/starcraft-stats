"""Tests for Application branch filtering logic."""

from starcraft_stats.application import Application, _parse_min_version


class TestParseMinVersion:
    def test_none_returns_none(self):
        assert _parse_min_version(None) is None

    def test_major_zero(self):
        assert _parse_min_version("0.0") == (0, 0)

    def test_simple_version(self):
        assert _parse_min_version("3.0") == (3, 0)

    def test_nonzero_minor(self):
        assert _parse_min_version("1.15") == (1, 15)

    def test_large_values(self):
        assert _parse_min_version("8.99") == (8, 99)


class TestLatestPerMajor:
    def test_no_branches(self):
        assert Application._latest_per_major([]) == []

    def test_single_branch(self):
        assert Application._latest_per_major(["hotfix/3.0"]) == ["hotfix/3.0"]

    def test_keeps_latest_minor_per_major(self):
        branches = ["hotfix/7.5", "hotfix/7.6", "hotfix/8.0", "hotfix/8.1"]
        assert Application._latest_per_major(branches) == ["hotfix/7.6", "hotfix/8.1"]

    def test_min_version_excludes_lower_major(self):
        branches = ["hotfix/2.3", "hotfix/3.0", "hotfix/4.1"]
        assert Application._latest_per_major(branches, min_version=(3, 0)) == [
            "hotfix/3.0",
            "hotfix/4.1",
        ]

    def test_min_version_excludes_lower_minor_same_major(self):
        # rockcraft case: exclude 1.x where x < 15
        branches = ["hotfix/1.14", "hotfix/1.15", "hotfix/1.16", "hotfix/2.0"]
        assert Application._latest_per_major(branches, min_version=(1, 15)) == [
            "hotfix/1.16",
            "hotfix/2.0",
        ]

    def test_min_version_exact_boundary_is_included(self):
        branches = ["hotfix/8.0", "hotfix/7.9"]
        assert Application._latest_per_major(branches, min_version=(8, 0)) == [
            "hotfix/8.0"
        ]

    def test_min_version_none_includes_all(self):
        branches = ["hotfix/1.0", "hotfix/2.0", "hotfix/3.0"]
        assert Application._latest_per_major(branches, min_version=None) == [
            "hotfix/1.0",
            "hotfix/2.0",
            "hotfix/3.0",
        ]

    def test_all_branches_excluded(self):
        branches = ["hotfix/1.0", "hotfix/2.0"]
        assert Application._latest_per_major(branches, min_version=(3, 0)) == []
