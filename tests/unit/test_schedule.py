"""Tests for schedule.py (ScheduleRefreshCommand distribution logic)."""

import argparse
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from starcraft_stats.models.github import GithubIssue, GithubIssues, Projects
from starcraft_stats.schedule import ScheduleRefreshCommand, distribute_refresh_dates


def _make_issue(opened_by: str | None = None) -> GithubIssue:
    return GithubIssue(
        type="issue",
        date_opened=datetime(2024, 1, 1, tzinfo=UTC),
        date_closed=None,
        refresh_date=datetime(2024, 1, 1, tzinfo=UTC),
        opened_by=opened_by,
    )


def _make_projects(counts: dict[str, int]) -> Projects:
    """Build a Projects model with the specified number of issues per project."""
    return Projects(
        projects={
            name: GithubIssues(issues={i + 1: _make_issue() for i in range(count)})
            for name, count in counts.items()
        }
    )


class TestScheduleRefreshDistribution:
    """Tests for the refresh-date distribution logic."""

    def _run_distribution(
        self,
        projects: Projects,
        interval: int,
        now: datetime,
    ) -> list[datetime]:
        all_issues = [
            (proj_name, issue_num)
            for proj_name, proj_issues in projects.projects.items()
            for issue_num in proj_issues.issues
        ]
        return distribute_refresh_dates(all_issues, projects, interval, now)

    def test_first_issue_expires_soonest(self):
        projects = _make_projects({"proj": 7})
        now = datetime(2026, 1, 8, tzinfo=UTC)
        dates = self._run_distribution(projects, interval=7, now=now)
        # First issue: ceil(1/7 * 7) = 1 day until expire → refresh_date = now - 6 days
        assert dates[0] == now - timedelta(days=6)

    def test_last_issue_expires_latest(self):
        projects = _make_projects({"proj": 7})
        now = datetime(2026, 1, 8, tzinfo=UTC)
        dates = self._run_distribution(projects, interval=7, now=now)
        # Last issue: ceil(7/7 * 7) = 7 days until expire → refresh_date = now
        assert dates[-1] == now

    def test_refresh_dates_are_monotonically_non_decreasing(self):
        projects = _make_projects({"proj": 20})
        now = datetime(2026, 1, 8, tzinfo=UTC)
        dates = self._run_distribution(projects, interval=7, now=now)
        for a, b in zip(dates, dates[1:]):
            assert a <= b

    def test_all_dates_within_interval_window(self):
        interval = 7
        projects = _make_projects({"proj": 14})
        now = datetime(2026, 1, 8, tzinfo=UTC)
        dates = self._run_distribution(projects, interval=interval, now=now)
        # First issue expires in 1 day, so its refresh_date is (now - (interval - 1))
        earliest = now - timedelta(days=interval - 1)
        for d in dates:
            assert earliest <= d <= now

    def test_multiple_projects_covered(self):
        projects = _make_projects({"alpha": 5, "beta": 5})
        now = datetime(2026, 1, 8, tzinfo=UTC)
        dates = self._run_distribution(projects, interval=7, now=now)
        assert len(dates) == 10
        assert dates[0] < dates[-1]

    def test_single_issue_gets_latest_refresh_date(self):
        projects = _make_projects({"proj": 1})
        now = datetime(2026, 1, 8, tzinfo=UTC)
        dates = self._run_distribution(projects, interval=7, now=now)
        # ceil(1/1 * 7) = 7 → refresh_date = now - 0 = now
        assert dates[0] == now


class TestScheduleRefreshCommand:
    """Integration-style tests for the full ScheduleRefreshCommand.run() flow."""

    @pytest.fixture
    def data_dir(self, tmp_path):
        (tmp_path / "html" / "data").mkdir(parents=True)
        return tmp_path

    @pytest.fixture
    def config_file(self, data_dir, monkeypatch):
        monkeypatch.chdir(data_dir)
        cfg = data_dir / "starcraft-config.toml"
        cfg.write_bytes(
            b"craft-libraries = []\n"
            b'craft-projects = ["proj-a", "proj-b"]\n'
            b"craft-applications = []\n"
            b"refresh-interval-days = 7\n"
        )
        return cfg

    @pytest.fixture
    def data_file(self, data_dir):
        return data_dir / "html" / "data" / "issues-github.yaml"

    def test_raises_if_data_file_missing(self, config_file):
        cmd = ScheduleRefreshCommand(config=None)
        with pytest.raises(RuntimeError, match="does not exist"):
            cmd.run(argparse.Namespace())

    def test_updates_refresh_dates_in_file(self, config_file, data_file):
        projects = _make_projects({"proj-a": 3, "proj-b": 3})
        projects.to_yaml_file(data_file)

        now = datetime(2026, 5, 1, tzinfo=UTC)
        cmd = ScheduleRefreshCommand(config=None)
        with patch("starcraft_stats.schedule.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = datetime
            cmd.run(argparse.Namespace())

        updated = Projects.from_yaml_file(data_file)
        all_dates = [
            issue.refresh_date
            for proj in updated.projects.values()
            for issue in proj.issues.values()
        ]
        # All dates should be within [now - 6 days, now]
        # (first issue expires in 1 day → refresh_date = now - (interval - 1))
        earliest = now - timedelta(days=6)
        for d in all_dates:
            assert earliest <= d <= now

    def test_empty_data_file_does_not_crash(self, config_file, data_file):
        Projects(projects={}).to_yaml_file(data_file)
        cmd = ScheduleRefreshCommand(config=None)
        # Should not raise; just emit a message
        cmd.run(argparse.Namespace())
