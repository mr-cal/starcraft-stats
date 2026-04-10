"""Tests for LaunchpadProject data collection and CSV generation."""

import csv as csv_module
import pathlib
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from starcraft_stats.launchpad import LaunchpadProject
from starcraft_stats.models.launchpad import (
    LaunchpadBug,
    LaunchpadBugs,
    LaunchpadProjects,
)

REAL_DATETIME = datetime


def _read_csv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open() as f:
        return list(csv_module.DictReader(f))


def _make_lp_task(
    bug_id: int, date_created: datetime, date_closed: datetime | None = None
) -> MagicMock:
    """Build a mock Launchpad bug_task object."""
    task = MagicMock()
    task.bug.id = bug_id
    task.date_created = date_created
    task.date_closed = date_closed
    return task


def _make_lp_project(tasks: list[MagicMock]) -> MagicMock:
    """Build a mock Launchpad project whose searchTasks returns tasks."""
    collection = MagicMock()
    collection.total_size = len(tasks)
    collection.__iter__ = MagicMock(return_value=iter(tasks))
    lp_project = MagicMock()
    lp_project.searchTasks.return_value = collection
    return lp_project


def _make_lp_api(lp_project: MagicMock) -> MagicMock:
    lp_api = MagicMock()
    lp_api.projects.__getitem__ = MagicMock(return_value=lp_project)
    return lp_api


@pytest.fixture
def launchpad_project_obj(tmp_path, monkeypatch):
    """A LaunchpadProject wired to a tmp_path working directory."""
    (tmp_path / "html" / "data").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    lp = LaunchpadProject.__new__(LaunchpadProject)
    lp.data_file = tmp_path / "html" / "data" / "issues-launchpad.yaml"
    lp._data = LaunchpadProjects(projects={})
    return lp


class TestUpdateDataFromLaunchpad:
    def test_bootstrap_stores_new_bugs(self, launchpad_project_obj):
        task1 = _make_lp_task(101, REAL_DATETIME(2020, 1, 1, tzinfo=UTC))
        task2 = _make_lp_task(
            102,
            REAL_DATETIME(2020, 6, 1, tzinfo=UTC),
            REAL_DATETIME(2021, 1, 1, tzinfo=UTC),
        )
        lp_proj = _make_lp_project([task1, task2])
        lp_api = _make_lp_api(lp_proj)

        with patch("starcraft_stats.launchpad.emit"):
            launchpad_project_obj.update_data_from_launchpad(lp_api, "snapcraft")

        bugs = launchpad_project_obj.data.projects["snapcraft"].bugs
        assert 101 in bugs
        assert 102 in bugs
        assert bugs[101].date_opened == REAL_DATETIME(2020, 1, 1, tzinfo=UTC)
        assert bugs[101].date_closed is None
        assert bugs[102].date_closed == REAL_DATETIME(2021, 1, 1, tzinfo=UTC)

    def test_bootstrap_uses_epoch_as_modified_since_when_no_data(
        self, launchpad_project_obj
    ):
        lp_proj = _make_lp_project([])
        lp_api = _make_lp_api(lp_proj)

        with patch("starcraft_stats.launchpad.emit"):
            launchpad_project_obj.update_data_from_launchpad(lp_api, "snapcraft")

        call_kwargs = lp_proj.searchTasks.call_args.kwargs
        assert call_kwargs["modified_since"] == REAL_DATETIME(1970, 1, 1, tzinfo=UTC)

    def test_bootstrap_spreads_refresh_dates_evenly(self, launchpad_project_obj):
        tasks = [
            _make_lp_task(i, REAL_DATETIME(2020, 1, 1, tzinfo=UTC)) for i in range(10)
        ]
        lp_proj = _make_lp_project(tasks)
        lp_api = _make_lp_api(lp_proj)

        with patch("starcraft_stats.launchpad.emit"):
            launchpad_project_obj.update_data_from_launchpad(
                lp_api, "snapcraft", refresh_interval_days=7
            )

        bugs = launchpad_project_obj.data.projects["snapcraft"].bugs
        refresh_dates = sorted(bug.refresh_date for bug in bugs.values())
        # Dates should be spread: oldest is ~7 days ago, newest is ~now
        spread = refresh_dates[-1] - refresh_dates[0]
        assert spread >= timedelta(days=6), f"Expected spread >=6 days, got {spread}"

    def test_incremental_uses_oldest_refresh_date(self, launchpad_project_obj):
        old_refresh = REAL_DATETIME(2025, 1, 1, tzinfo=UTC)
        new_refresh = REAL_DATETIME(2026, 1, 1, tzinfo=UTC)
        bug_old = LaunchpadBug(
            date_opened=REAL_DATETIME(2020, 1, 1, tzinfo=UTC),
            date_closed=None,
            refresh_date=old_refresh,
        )
        bug_new = LaunchpadBug(
            date_opened=REAL_DATETIME(2020, 6, 1, tzinfo=UTC),
            date_closed=None,
            refresh_date=new_refresh,
        )
        launchpad_project_obj._data = LaunchpadProjects(
            projects={"snapcraft": LaunchpadBugs(bugs={1: bug_old, 2: bug_new})}
        )

        lp_proj = _make_lp_project([])
        lp_api = _make_lp_api(lp_proj)

        with patch("starcraft_stats.launchpad.emit"):
            launchpad_project_obj.update_data_from_launchpad(lp_api, "snapcraft")

        call_kwargs = lp_proj.searchTasks.call_args.kwargs
        assert call_kwargs["modified_since"] == old_refresh

    def test_existing_bug_is_updated_not_duplicated(self, launchpad_project_obj):
        existing_bug = LaunchpadBug(
            date_opened=REAL_DATETIME(2020, 1, 1, tzinfo=UTC),
            date_closed=None,
            refresh_date=REAL_DATETIME(2025, 1, 1, tzinfo=UTC),
        )
        launchpad_project_obj._data = LaunchpadProjects(
            projects={"snapcraft": LaunchpadBugs(bugs={101: existing_bug})}
        )
        updated_task = _make_lp_task(
            101,
            REAL_DATETIME(2020, 1, 1, tzinfo=UTC),
            REAL_DATETIME(2026, 1, 1, tzinfo=UTC),
        )
        lp_proj = _make_lp_project([updated_task])
        lp_api = _make_lp_api(lp_proj)

        with patch("starcraft_stats.launchpad.emit"):
            launchpad_project_obj.update_data_from_launchpad(lp_api, "snapcraft")

        bugs = launchpad_project_obj.data.projects["snapcraft"].bugs
        assert len(bugs) == 1
        assert bugs[101].date_closed == REAL_DATETIME(2026, 1, 1, tzinfo=UTC)

    def test_stale_refresh_no_matching_task_updates_refresh_date(
        self, launchpad_project_obj
    ):
        """A stale bug whose task is no longer found still gets refresh_date bumped."""
        stale_date = REAL_DATETIME(2020, 1, 1, tzinfo=UTC)
        existing_bug = LaunchpadBug(
            date_opened=REAL_DATETIME(2019, 1, 1, tzinfo=UTC),
            date_closed=None,
            refresh_date=stale_date,
        )
        launchpad_project_obj._data = LaunchpadProjects(
            projects={"snapcraft": LaunchpadBugs(bugs={101: existing_bug})}
        )
        # Incremental fetch returns nothing new
        lp_proj = _make_lp_project([])
        lp_api = _make_lp_api(lp_proj)

        # Make the bug lookup return a bug whose tasks don't include "snapcraft"
        lp_bug_mock = MagicMock()
        lp_bug_mock.bug_tasks = []  # no matching task
        lp_api.bugs.__getitem__ = MagicMock(return_value=lp_bug_mock)

        with patch("starcraft_stats.launchpad.emit"):
            launchpad_project_obj.update_data_from_launchpad(
                lp_api, "snapcraft", refresh_interval_days=1
            )

        bugs = launchpad_project_obj.data.projects["snapcraft"].bugs
        assert bugs[101].refresh_date > stale_date, (
            "refresh_date should be updated even when task is not found"
        )


class TestLaunchpadProjectGenerateCsv:
    def _make_bug(self, opened, closed=None):
        return LaunchpadBug(
            date_opened=opened,
            date_closed=closed,
            refresh_date=REAL_DATETIME(2026, 1, 1, tzinfo=UTC),
        )

    def _generate(self, lp_obj, project, end_date):
        with (
            patch("starcraft_stats.launchpad.datetime") as mock_dt,
            patch("starcraft_stats.launchpad.emit"),
        ):
            mock_dt.now.return_value = end_date
            mock_dt.side_effect = REAL_DATETIME
            lp_obj.generate_csv(project)

    def test_csv_headers_match_issue_data_point_format(
        self, launchpad_project_obj, tmp_path
    ):
        bug = self._make_bug(REAL_DATETIME(2015, 1, 2, tzinfo=UTC))
        launchpad_project_obj._data = LaunchpadProjects(
            projects={"snapcraft": LaunchpadBugs(bugs={1: bug})}
        )
        self._generate(
            launchpad_project_obj, "snapcraft", REAL_DATETIME(2015, 1, 4, tzinfo=UTC)
        )

        content = (tmp_path / "html/data/snapcraft-launchpad.csv").read_text()
        assert content.startswith("date,issues,closed,age")

    def test_open_bug_counted_correctly(self, launchpad_project_obj, tmp_path):
        bug = self._make_bug(REAL_DATETIME(2015, 1, 2, tzinfo=UTC))
        launchpad_project_obj._data = LaunchpadProjects(
            projects={"snapcraft": LaunchpadBugs(bugs={1: bug})}
        )
        self._generate(
            launchpad_project_obj, "snapcraft", REAL_DATETIME(2015, 1, 5, tzinfo=UTC)
        )

        rows = _read_csv(tmp_path / "html/data/snapcraft-launchpad.csv")
        assert rows[0]["issues"] == "0"  # Jan 1: not yet open
        assert rows[1]["issues"] == "0"  # Jan 2: opened < date is strict
        assert rows[2]["issues"] == "1"  # Jan 3: open
        assert rows[3]["issues"] == "1"  # Jan 4: open

    def test_closed_bug_counted_on_close_date(self, launchpad_project_obj, tmp_path):
        bug = self._make_bug(
            REAL_DATETIME(2015, 1, 1, tzinfo=UTC),
            closed=REAL_DATETIME(2015, 1, 3, tzinfo=UTC),
        )
        launchpad_project_obj._data = LaunchpadProjects(
            projects={"snapcraft": LaunchpadBugs(bugs={1: bug})}
        )
        self._generate(
            launchpad_project_obj, "snapcraft", REAL_DATETIME(2015, 1, 5, tzinfo=UTC)
        )

        rows = _read_csv(tmp_path / "html/data/snapcraft-launchpad.csv")
        assert rows[1]["closed"] == "0"
        assert rows[2]["closed"] == "1"
        assert rows[3]["closed"] == "0"

    def test_missing_project_skips_csv(self, launchpad_project_obj, tmp_path):
        with patch("starcraft_stats.launchpad.emit"):
            launchpad_project_obj.generate_csv("snapcraft")

        assert not (tmp_path / "html/data/snapcraft-launchpad.csv").exists()

    def test_csv_file_path(self):
        assert LaunchpadProject.csv_file("snapcraft") == pathlib.Path(
            "html/data/snapcraft-launchpad.csv"
        )
