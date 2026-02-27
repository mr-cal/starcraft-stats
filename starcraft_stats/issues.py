"""Module for github data collection."""

import argparse
import json
import os
import pathlib
from datetime import UTC, datetime, timedelta

from craft_cli import BaseCommand, emit
from github import Github, GithubException

from .config import CONFIG_FILE, Config
from .models import (
    GithubIssue,
    GithubIssues,
    IntermediateData,
    IntermediateDataPoint,
    IssueDataPoint,
    Projects,
)


class GithubProject:
    """Class for a github project.

    This class can load data from a file, update that data from github,
    and save the data to a file.

    It also generates a CSV file ready for visualization.

    :cvar owner: The owner of the project.
    :cvar data_file: The path to the shared local data file, written as yaml.
    """

    owner: str
    data_file: pathlib.Path

    def __init__(self, owner: str = "canonical") -> None:
        self.owner = owner
        self.data_file = pathlib.Path("html/data/issues-github.yaml")
        self._data = self._load_data()

    def _load_data(self) -> Projects:
        """Load issue data from the local YAML file, or return an empty store."""
        if self.data_file.exists():
            emit.progress(f"Loading data from {self.data_file}", permanent=True)
            return Projects.from_yaml_file(self.data_file)
        emit.message(f"Data file {self.data_file} does not exist.")
        return Projects(projects={})

    @property
    def data(self) -> Projects:
        """The in-memory issue data store."""
        return self._data

    @staticmethod
    def csv_file(project: str) -> pathlib.Path:
        """Get the csv file for a project."""
        if project == "all":
            return pathlib.Path("html/data/all-projects-github.csv")
        return pathlib.Path(f"html/data/{project}-github.csv")

    @staticmethod
    def _issue_from_api(api_issue: object, now: datetime) -> GithubIssue:
        """Construct a GithubIssue from a PyGithub issue object."""
        return GithubIssue(
            type="issue" if api_issue.pull_request is None else "pr",  # type: ignore[union-attr]
            date_opened=api_issue.created_at,  # type: ignore[union-attr]
            date_closed=api_issue.closed_at,  # type: ignore[union-attr]
            refresh_date=now,
        )

    def update_data_from_github(
        self, github_api: Github, project: str, refresh_interval_days: int = 7
    ) -> None:
        """Update local data about issues from github.

        Only fetches issues that haven't been refreshed in the specified interval,
        and always checks for new issues.

        :param github_api: GitHub API client
        :param project: Project name
        :param refresh_interval_days: Number of days before refreshing an issue
        """
        emit.progress(f"Collecting data for {self.owner}/{project}", permanent=True)

        # Initialize project if it doesn't exist
        if project not in self.data.projects:
            emit.debug(f"Creating new project in data file {project}")
            self.data.projects[project] = GithubIssues(issues={})

        now = datetime.now()
        refresh_threshold = timedelta(days=refresh_interval_days)
        repo = github_api.get_repo(f"{self.owner}/{project}")

        # Find issues that need refreshing (haven't been updated in threshold days)
        issues_to_refresh = [
            issue_num
            for issue_num, issue in self.data.projects[project].issues.items()
            if (now - issue.refresh_date) > refresh_threshold
        ]
        emit.debug(f"Found {len(issues_to_refresh)} existing issues to refresh")

        # Refresh stale issues
        for issue_num in issues_to_refresh:
            try:
                api_issue = repo.get_issue(number=issue_num)
                self.data.projects[project].issues[issue_num] = self._issue_from_api(
                    api_issue, now
                )
                emit.debug(f"Refreshed issue {issue_num}")
            except GithubException as e:
                emit.debug(f"Could not fetch issue {issue_num}: {e}")

        # Check for new issues starting from the highest known issue number
        max_issue_num = max(self.data.projects[project].issues.keys(), default=0)
        emit.debug(f"Highest existing issue number: {max_issue_num}")

        new_issues_found = 0
        next_issue_num = max_issue_num + 1
        consecutive_not_found = 0
        max_consecutive_not_found = 5  # Stop after 5 consecutive missing issues

        while consecutive_not_found < max_consecutive_not_found:
            try:
                api_issue = repo.get_issue(number=next_issue_num)
                self.data.projects[project].issues[next_issue_num] = (
                    self._issue_from_api(api_issue, now)
                )
                emit.debug(f"Found new issue {next_issue_num}")
                new_issues_found += 1
                consecutive_not_found = 0
            except GithubException:
                consecutive_not_found += 1

            next_issue_num += 1

        emit.progress(
            f"Refreshed {len(issues_to_refresh)} issues, found {new_issues_found} new issues for {project}",
            permanent=True,
        )

    def save_data_to_file(self) -> None:
        """Write data to a local file."""
        emit.progress(f"Writing data to {self.data_file}")
        self.data.to_yaml_file(self.data_file)
        emit.message(f"Wrote to {self.data_file}")

    def generate_csv(self, project: str) -> None:
        """Generate a CSV file from issue data.

        Iterates through each day from the start date to today, counts open issues
        and computes median age, then writes the results to a CSV file.

        Data is organized as:
        | date       | open issues | closed | age |
        | ---------- | ----------- | ------ | --- |
        | 2021-01-01 | 10          | 2      | 20  |
        | ...        | ...         | ...    | ... |
        """
        start_date = datetime(year=2021, month=1, day=1, tzinfo=UTC)
        end_date = datetime.now(tz=UTC)

        # Collect the flat list of issues to count once, before the per-day loop
        if project == "all":
            issues = [
                issue
                for proj in self.data.projects.values()
                for issue in proj.issues.values()
            ]
        else:
            issues = list(self.data.projects[project].issues.values())

        intermediate_data = IntermediateData()
        emit.progress(f"Counting open issues and age for {project}")

        for date in [
            start_date + timedelta(days=i) for i in range((end_date - start_date).days)
        ]:
            open_issues = [issue for issue in issues if issue.is_open(date)]
            closed_today = sum(
                1
                for issue in issues
                if issue.date_closed is not None
                and issue.date_closed.date() == date.date()
            )
            intermediate_data.data.append(
                IntermediateDataPoint(
                    date=date.strftime("%Y-%b-%d"),
                    open_issues=len(open_issues),
                    closed_issues=closed_today,
                    mean_age=get_median_age(
                        [issue.date_opened for issue in open_issues],
                        date,
                    ),
                ),
            )

        csv_file = self.csv_file(str(project))
        emit.debug(f"Writing data to {csv_file}")
        IssueDataPoint.save_to_csv(intermediate_data.to_csv_models(), csv_file)
        emit.progress(f"Wrote to {csv_file}", permanent=True)

    def generate_snapshot(self, projects: list[str]) -> None:
        """Generate a point-in-time snapshot JSON for the comparison charts.

        For each project, computes open issues, open PRs, median age of open issues,
        median age of open PRs, and issues/PRs closed in the last year.

        :param projects: Ordered list of project names to include.
        """
        now = datetime.now(tz=UTC)
        one_year_ago = now - timedelta(days=365)

        snapshot: dict[str, dict[str, int | None]] = {}
        for project in projects:
            if project not in self.data.projects:
                continue
            issues = list(self.data.projects[project].issues.values())

            open_issues = [i for i in issues if i.type == "issue" and i.is_open(now)]
            open_prs = [i for i in issues if i.type == "pr" and i.is_open(now)]

            snapshot[project] = {
                "open_issues": len(open_issues),
                "open_prs": len(open_prs),
                "median_issue_age": get_median_age(
                    [i.date_opened for i in open_issues], now
                ),
                "median_pr_age": get_median_age([i.date_opened for i in open_prs], now),
                "closed_issues_year": sum(
                    1
                    for i in issues
                    if i.type == "issue"
                    and i.date_closed is not None
                    and i.date_closed >= one_year_ago
                ),
                "closed_prs_year": sum(
                    1
                    for i in issues
                    if i.type == "pr"
                    and i.date_closed is not None
                    and i.date_closed >= one_year_ago
                ),
            }

        snapshot_file = pathlib.Path("html/data/snapshot.json")
        snapshot_file.write_text(json.dumps(snapshot, indent=2) + "\n")
        emit.progress(f"Wrote snapshot to {snapshot_file}", permanent=True)


def load_github_token() -> str:
    """Load a github token from the environment.

    Accept `STARCRAFT_GITHUB_TOKEN` because a personal fine-grained token has a max of
    5,000 API requests per hour whereas the `GITHUB_TOKEN` provided by GitHub Actions
    only allows 1,000 API requests per hour.
    """
    token = os.getenv("STARCRAFT_GITHUB_TOKEN")
    if token:
        emit.debug("Loaded STARCRAFT_GITHUB_TOKEN from environment")
        return token

    token = os.getenv("GITHUB_TOKEN")
    if token:
        emit.debug("Loaded GITHUB_TOKEN from environment")
    else:
        raise RuntimeError(
            "Could not connect to github because environment "
            "variable GITHUB_TOKEN is not set",
        )
    return token


class GetIssuesCommand(BaseCommand):
    """Collect data about issues and PRs for a set of github projects.

    Intermediate data about each issue in a project is stored in a yaml file.
    Then, this data is processed into a CSV file for visualization.
    """

    name = "get-issues"
    help_msg = "Collect data on open issues from github"
    overview = "Collect data on open issues from github"
    common = True

    def run(
        self,
        parsed_args: argparse.Namespace,  # noqa: ARG002 (Unused method argument)
    ) -> None:
        """Collect data on open issues from github.

        :param parsed_args: parsed command line arguments
        """
        config = Config.from_yaml_file(CONFIG_FILE)
        github_token = load_github_token()
        github_api = Github(github_token)
        github_project = GithubProject()

        # iterate through all projects
        for project in config.craft_projects:
            github_project.update_data_from_github(
                github_api, project, config.refresh_interval_days
            )
            github_project.save_data_to_file()
            github_project.generate_csv(project)

        # generate csv and save data for all projects
        github_project.generate_csv("all")

        # write the project list for the frontend
        projects_file = pathlib.Path("html/data/projects.json")
        projects_data = {
            "applications": sorted(config.craft_applications),
            "libraries": sorted(config.craft_libraries),
        }
        projects_file.write_text(json.dumps(projects_data, indent=2) + "\n")
        emit.progress(f"Wrote projects list to {projects_file}", permanent=True)

        # write the snapshot for the comparison charts
        github_project.generate_snapshot(config.craft_projects)


def get_median_age(dates: list[datetime] | None, date: datetime) -> int | None:
    """Get the median age in days of a list of dates from a reference date."""
    if dates:
        median_date = get_median_date(dates)
        return (date - median_date).days

    return None


def get_mean_date(dates: list[datetime]) -> datetime:
    """Get mean date from a list of datetimes."""
    reference = datetime(year=2000, month=1, day=1, tzinfo=UTC)
    return reference + sum((date - reference for date in dates), timedelta()) / len(
        dates,
    )


def get_median_date(dates: list[datetime]) -> datetime:
    """Get median date from a list of datetimes."""
    if len(dates) == 0:
        raise ValueError("Cannot get median date from an empty list")

    sorted_dates = sorted(dates)
    n = len(sorted_dates)

    # if the list is even, average the two middle values
    if n % 2 == 0:
        return get_mean_date(sorted_dates[n // 2 - 1 : n // 2 + 1])

    # if the list is odd, return the middle value
    return sorted_dates[n // 2]
