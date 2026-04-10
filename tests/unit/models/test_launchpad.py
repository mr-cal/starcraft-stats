"""Tests for LaunchpadBug model."""

from datetime import UTC, datetime

from starcraft_stats.models.launchpad import (
    LaunchpadBug,
    LaunchpadBugs,
    LaunchpadProjects,
)


class TestLaunchpadBugIsOpen:
    def _make_bug(self, opened, closed=None):
        return LaunchpadBug(
            date_opened=opened,
            date_closed=closed,
            refresh_date=datetime(2026, 1, 1, tzinfo=UTC),
        )

    def test_open_bug_is_open_after_creation(self):
        bug = self._make_bug(opened=datetime(2024, 1, 1, tzinfo=UTC))
        assert bug.is_open(datetime(2024, 6, 1, tzinfo=UTC))

    def test_bug_not_open_before_creation(self):
        bug = self._make_bug(opened=datetime(2024, 6, 1, tzinfo=UTC))
        assert not bug.is_open(datetime(2024, 1, 1, tzinfo=UTC))

    def test_bug_not_open_on_exact_creation_date(self):
        opened = datetime(2024, 1, 1, tzinfo=UTC)
        bug = self._make_bug(opened=opened)
        assert not bug.is_open(opened)

    def test_closed_bug_not_open_after_close(self):
        bug = self._make_bug(
            opened=datetime(2024, 1, 1, tzinfo=UTC),
            closed=datetime(2024, 3, 1, tzinfo=UTC),
        )
        assert not bug.is_open(datetime(2024, 6, 1, tzinfo=UTC))

    def test_closed_bug_open_before_close(self):
        bug = self._make_bug(
            opened=datetime(2024, 1, 1, tzinfo=UTC),
            closed=datetime(2024, 6, 1, tzinfo=UTC),
        )
        assert bug.is_open(datetime(2024, 3, 1, tzinfo=UTC))

    def test_closed_bug_not_open_on_exact_close_date(self):
        closed = datetime(2024, 3, 1, tzinfo=UTC)
        bug = self._make_bug(
            opened=datetime(2024, 1, 1, tzinfo=UTC),
            closed=closed,
        )
        assert not bug.is_open(closed)


class TestLaunchpadBugsModel:
    def test_empty_by_default(self):
        bugs = LaunchpadBugs()
        assert bugs.bugs == {}

    def test_stores_bugs_by_id(self):
        bug = LaunchpadBug(
            date_opened=datetime(2024, 1, 1, tzinfo=UTC),
            date_closed=None,
            refresh_date=datetime(2026, 1, 1, tzinfo=UTC),
        )
        bugs = LaunchpadBugs(bugs={42: bug})
        assert bugs.bugs[42] is bug


class TestLaunchpadProjectsModel:
    def test_empty_by_default(self):
        projects = LaunchpadProjects()
        assert projects.projects == {}

    def test_yaml_roundtrip(self, tmp_path):
        bug = LaunchpadBug(
            date_opened=datetime(2024, 1, 1, tzinfo=UTC),
            date_closed=datetime(2024, 6, 1, tzinfo=UTC),
            refresh_date=datetime(2026, 1, 1, tzinfo=UTC),
        )
        projects = LaunchpadProjects(
            projects={"snapcraft": LaunchpadBugs(bugs={123: bug})}
        )
        yaml_file = tmp_path / "issues-launchpad.yaml"
        projects.to_yaml_file(yaml_file)

        loaded = LaunchpadProjects.from_yaml_file(yaml_file)
        assert "snapcraft" in loaded.projects
        loaded_bug = loaded.projects["snapcraft"].bugs[123]
        assert loaded_bug.date_opened == bug.date_opened
        assert loaded_bug.date_closed == bug.date_closed
