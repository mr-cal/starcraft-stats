"""Tests for issues.py utility functions and GithubProject logic."""

import csv as csv_module
import pathlib
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from starcraft_stats.issues import (
    GithubProject,
    get_mean_date,
    get_median_age,
    get_median_date,
    load_github_token,
)
from starcraft_stats.models.github import GithubIssue, GithubIssues, Projects

REAL_DATETIME = datetime


def _read_csv(path: pathlib.Path) -> list[dict[str, str]]:
    """Read a CSV file into a list of row dicts."""
    with path.open() as f:
        return list(csv_module.DictReader(f))


class TestGetMedianDate:
    def test_odd_list_returns_middle_element(self):
        dates = [
            datetime(2024, 1, 1, tzinfo=UTC),
            datetime(2024, 1, 10, tzinfo=UTC),
            datetime(2024, 1, 20, tzinfo=UTC),
        ]
        assert get_median_date(dates) == datetime(2024, 1, 10, tzinfo=UTC)

    def test_even_list_returns_mean_of_two_middle_elements(self):
        dates = [
            datetime(2024, 1, 1, tzinfo=UTC),
            datetime(2024, 1, 3, tzinfo=UTC),
            datetime(2024, 1, 5, tzinfo=UTC),
            datetime(2024, 1, 10, tzinfo=UTC),
        ]
        # Middle two are Jan 3 and Jan 5; mean = Jan 4
        assert get_median_date(dates) == datetime(2024, 1, 4, tzinfo=UTC)

    def test_single_element_returns_that_date(self):
        date = datetime(2024, 6, 15, tzinfo=UTC)
        assert get_median_date([date]) == date

    def test_empty_list_raises_value_error(self):
        with pytest.raises(ValueError, match="empty"):
            get_median_date([])


class TestGetMeanDate:
    def test_two_equidistant_dates_return_midpoint(self):
        d1 = datetime(2024, 1, 1, tzinfo=UTC)
        d2 = datetime(2024, 1, 11, tzinfo=UTC)
        assert get_mean_date([d1, d2]) == datetime(2024, 1, 6, tzinfo=UTC)

    def test_single_date_returns_that_date(self):
        date = datetime(2024, 3, 15, tzinfo=UTC)
        assert get_mean_date([date]) == date


class TestGetMedianAge:
    def test_none_returns_none(self):
        assert get_median_age(None, datetime(2024, 1, 1, tzinfo=UTC)) is None

    def test_empty_list_returns_none(self):
        assert get_median_age([], datetime(2024, 1, 1, tzinfo=UTC)) is None

    def test_single_date_returns_days_since_opened(self):
        opened = datetime(2024, 1, 1, tzinfo=UTC)
        reference = datetime(2024, 1, 21, tzinfo=UTC)
        assert get_median_age([opened], reference) == 20

    def test_multiple_dates_uses_median(self):
        dates = [
            datetime(2024, 1, 1, tzinfo=UTC),
            datetime(2024, 1, 11, tzinfo=UTC),
            datetime(2024, 1, 21, tzinfo=UTC),
        ]
        reference = datetime(2024, 1, 31, tzinfo=UTC)
        # median date is Jan 11, age = 31 - 11 = 20 days
        assert get_median_age(dates, reference) == 20


class TestLoadGithubToken:
    def test_starcraft_token_takes_priority_over_github_token(self, monkeypatch):
        monkeypatch.setenv("STARCRAFT_GITHUB_TOKEN", "starcraft-token")
        monkeypatch.setenv("GITHUB_TOKEN", "github-token")
        assert load_github_token() == "starcraft-token"

    def test_falls_back_to_github_token(self, monkeypatch):
        monkeypatch.delenv("STARCRAFT_GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GITHUB_TOKEN", "github-token")
        assert load_github_token() == "github-token"

    def test_only_starcraft_token_set(self, monkeypatch):
        monkeypatch.setenv("STARCRAFT_GITHUB_TOKEN", "starcraft-token")
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        assert load_github_token() == "starcraft-token"

    def test_neither_token_raises_runtime_error(self, monkeypatch):
        monkeypatch.delenv("STARCRAFT_GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        with pytest.raises(RuntimeError, match="GITHUB_TOKEN"):
            load_github_token()


class TestGithubProjectCsvFile:
    def test_all_returns_all_projects_csv(self):
        assert GithubProject.csv_file("all") == pathlib.Path(
            "html/data/all-projects-github.csv"
        )

    def test_named_project_returns_project_csv(self):
        assert GithubProject.csv_file("craft-cli") == pathlib.Path(
            "html/data/craft-cli-github.csv"
        )


class TestGithubProjectGenerateCsv:
    """Tests for GithubProject.generate_csv."""

    @pytest.fixture
    def github_project(self, tmp_path, monkeypatch):
        (tmp_path / "html" / "data").mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        gp = GithubProject.__new__(GithubProject)
        gp.owner = "canonical"
        gp.data_file = tmp_path / "issues.yaml"
        gp._data = Projects(projects={})
        return gp

    def _make_issue(self, opened, closed=None):
        return GithubIssue(
            type="issue",
            date_opened=opened,
            date_closed=closed,
            refresh_date=datetime(2026, 1, 1, tzinfo=UTC),
        )

    def _generate(self, gp, project, end_date):
        """Run generate_csv with a fixed end date."""
        with (
            patch("starcraft_stats.issues.datetime") as mock_dt,
            patch("starcraft_stats.issues.emit"),
        ):
            mock_dt.now.return_value = end_date
            mock_dt.side_effect = REAL_DATETIME
            gp.generate_csv(project)

    def test_empty_project_produces_all_zero_rows(self, github_project, tmp_path):
        github_project._data = Projects(projects={"proj": GithubIssues(issues={})})
        self._generate(github_project, "proj", REAL_DATETIME(2021, 1, 4, tzinfo=UTC))

        rows = _read_csv(tmp_path / "html/data/proj-github.csv")
        assert all(r["issues"] == "0" for r in rows)
        assert all(r["closed"] == "0" for r in rows)

    def test_open_issues_counted_on_correct_dates(self, github_project, tmp_path):
        issue = self._make_issue(opened=REAL_DATETIME(2021, 1, 2, tzinfo=UTC))
        github_project._data = Projects(
            projects={"proj": GithubIssues(issues={1: issue})}
        )
        self._generate(github_project, "proj", REAL_DATETIME(2021, 1, 5, tzinfo=UTC))

        rows = _read_csv(tmp_path / "html/data/proj-github.csv")
        assert rows[0]["issues"] == "0"  # Jan 1: not opened yet
        assert rows[1]["issues"] == "0"  # Jan 2: opened < date is strict
        assert rows[2]["issues"] == "1"  # Jan 3: open
        assert rows[3]["issues"] == "1"  # Jan 4: open

    def test_closed_issue_counted_only_on_close_date(self, github_project, tmp_path):
        issue = self._make_issue(
            opened=REAL_DATETIME(2021, 1, 1, tzinfo=UTC),
            closed=REAL_DATETIME(2021, 1, 3, tzinfo=UTC),
        )
        github_project._data = Projects(
            projects={"proj": GithubIssues(issues={1: issue})}
        )
        self._generate(github_project, "proj", REAL_DATETIME(2021, 1, 5, tzinfo=UTC))

        rows = _read_csv(tmp_path / "html/data/proj-github.csv")
        assert rows[0]["closed"] == "0"  # Jan 1
        assert rows[1]["closed"] == "0"  # Jan 2
        assert rows[2]["closed"] == "1"  # Jan 3: closed this day
        assert rows[3]["closed"] == "0"  # Jan 4

    def test_multiple_issues_closed_same_day(self, github_project, tmp_path):
        close_date = REAL_DATETIME(2021, 1, 2, tzinfo=UTC)
        issues = {
            i: self._make_issue(
                opened=REAL_DATETIME(2021, 1, 1, tzinfo=UTC),
                closed=close_date,
            )
            for i in range(1, 4)
        }
        github_project._data = Projects(projects={"proj": GithubIssues(issues=issues)})
        self._generate(github_project, "proj", REAL_DATETIME(2021, 1, 4, tzinfo=UTC))

        rows = _read_csv(tmp_path / "html/data/proj-github.csv")
        assert rows[1]["closed"] == "3"  # Jan 2: all 3 closed

    def test_all_aggregates_open_issues_across_projects(self, github_project, tmp_path):
        issue_a = self._make_issue(opened=REAL_DATETIME(2021, 1, 1, tzinfo=UTC))
        issue_b = self._make_issue(opened=REAL_DATETIME(2021, 1, 1, tzinfo=UTC))
        github_project._data = Projects(
            projects={
                "proj-a": GithubIssues(issues={1: issue_a}),
                "proj-b": GithubIssues(issues={1: issue_b}),
            }
        )
        self._generate(github_project, "all", REAL_DATETIME(2021, 1, 4, tzinfo=UTC))

        rows = _read_csv(tmp_path / "html/data/all-projects-github.csv")
        assert rows[1]["issues"] == "2"  # Jan 2: both open

    def test_all_aggregates_closed_issues_across_projects(
        self, github_project, tmp_path
    ):
        close_date = REAL_DATETIME(2021, 1, 3, tzinfo=UTC)
        issue_a = self._make_issue(
            opened=REAL_DATETIME(2021, 1, 1, tzinfo=UTC), closed=close_date
        )
        issue_b = self._make_issue(
            opened=REAL_DATETIME(2021, 1, 1, tzinfo=UTC), closed=close_date
        )
        github_project._data = Projects(
            projects={
                "proj-a": GithubIssues(issues={1: issue_a}),
                "proj-b": GithubIssues(issues={1: issue_b}),
            }
        )
        self._generate(github_project, "all", REAL_DATETIME(2021, 1, 5, tzinfo=UTC))

        rows = _read_csv(tmp_path / "html/data/all-projects-github.csv")
        assert rows[2]["closed"] == "2"  # Jan 3: both closed

    def test_csv_headers_are_correct(self, github_project, tmp_path):
        github_project._data = Projects(projects={"proj": GithubIssues(issues={})})
        self._generate(github_project, "proj", REAL_DATETIME(2021, 1, 3, tzinfo=UTC))

        content = (tmp_path / "html/data/proj-github.csv").read_text()
        assert content.startswith("date,issues,closed,age")
