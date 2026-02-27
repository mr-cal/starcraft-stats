"""Module for github data collection."""

import argparse
import json
import os
import pathlib
from datetime import UTC, datetime, timedelta
from functools import cached_property

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
    :cvar __data: Data about the project's issues.
    :cvar data_file: The path to the shared local data file, written as yaml.
    """

    owner: str
    __data: Projects | None = None
    data_file: pathlib.Path

    def __init__(self, owner: str = "canonical") -> None:
        self.owner = owner
        self.data_file = pathlib.Path("html/data/issues-github.yaml")
        self.get_data()

    def get_data(self) -> Projects:
        """Load a local data file containing Github issues for a project."""
        if self.__data:
            return self.__data

        if self.data_file.exists():
            emit.progress(f"Loading data from {self.data_file}", permanent=True)
            data: Projects = Projects.from_yaml_file(self.data_file)
        else:
            emit.message(f"Data file {self.data_file} does not exist.")
            data = Projects(projects={})

        self.__data = data
        return data

    @cached_property
    def data(self) -> Projects:
        """Get the data for the project."""
        return self.get_data()

    @staticmethod
    def csv_file(project: str) -> pathlib.Path:
        """Get the csv file for a project."""
        if project == "all":
            return pathlib.Path("html/data/all-projects-github.csv")
        return pathlib.Path(f"html/data/{project}-github.csv")

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

        now = datetime.now(tz=UTC)
        refresh_threshold = timedelta(days=refresh_interval_days)

        # Find issues that need refreshing (haven't been updated in threshold days)
        issues_to_refresh = []
        for issue_num, issue in self.data.projects[project].issues.items():
            if (now - issue.refresh_date) > refresh_threshold:
                issues_to_refresh.append(issue_num)

        emit.debug(f"Found {len(issues_to_refresh)} existing issues to refresh")

        # Refresh stale issues
        for issue_num in issues_to_refresh:
            try:
                issue = github_api.get_repo(f"{self.owner}/{project}").get_issue(
                    number=issue_num
                )
                self.data.projects[project].issues[issue_num] = GithubIssue(
                    type="issue" if issue.pull_request is None else "pr",
                    date_opened=issue.created_at,
                    date_closed=issue.closed_at,
                    refresh_date=now,
                )
                emit.debug(f"Refreshed issue {issue_num}")
            except GithubException as e:
                emit.debug(f"Could not fetch issue {issue_num}: {e}")

        # Find the highest issue number we have
        max_issue_num = max(self.data.projects[project].issues.keys(), default=0)
        emit.debug(f"Highest existing issue number: {max_issue_num}")

        # Check for new issues starting from max_issue_num + 1
        new_issues_found = 0
        next_issue_num = max_issue_num + 1
        consecutive_not_found = 0
        max_consecutive_not_found = 5  # Stop after 5 consecutive missing issues

        while consecutive_not_found < max_consecutive_not_found:
            try:
                issue = github_api.get_repo(f"{self.owner}/{project}").get_issue(
                    number=next_issue_num
                )
                # Issue exists!
                self.data.projects[project].issues[next_issue_num] = GithubIssue(
                    type="issue" if issue.pull_request is None else "pr",
                    date_opened=issue.created_at,
                    date_closed=issue.closed_at,
                    refresh_date=now,
                )
                emit.debug(f"Found new issue {next_issue_num}")
                new_issues_found += 1
                consecutive_not_found = 0  # Reset counter
            except GithubException:
                # Issue doesn't exist (404 or other error)
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
        """Generate a CSV file from a GithubIssues object.

        Iterates through each day from the start date to today, counts open issues
        and computes median age, then writes the results to a CSV file.

        Data is organized as:
        | date       | open issues | mean age  |
        | ---------- | ----------- | --------- |
        | 2021-01-01 | 10          | 20        |
        | ...        | ...         | ...       |
        """
        # intermediate data structure of
        intermediate_data = IntermediateData()

        start_date = datetime(year=2021, month=1, day=1, tzinfo=UTC)
        end_date = datetime.now(tz=UTC)

        # iterate through each day from start_date to end_date
        emit.progress(f"Counting open issues and age for {project}")
        for date in [
            start_date + timedelta(days=i) for i in range((end_date - start_date).days)
        ]:
            if project == "all":
                open_issues = [
                    issue
                    for project in self.data.projects.values()
                    for issue in project.issues.values()
                    if issue.is_open(date)
                ]
            else:
                open_issues = [
                    issue
                    for issue in self.data.projects[project].issues.values()
                    if issue.is_open(date)
                ]
            mean_age = get_median_age(
                [issue.date_opened for issue in open_issues],
                date,
            )
            intermediate_data.data.append(
                IntermediateDataPoint(
                    date=date.strftime("%Y-%b-%d"),
                    open_issues=len(open_issues),
                    mean_age=mean_age,
                ),
            )

        csv_file = self.csv_file(str(project))
        emit.debug(f"Writing data to {csv_file}")
        csv_models = intermediate_data.to_csv_models()
        IssueDataPoint.save_to_csv(csv_models, csv_file)
        emit.progress(f"Wrote to {csv_file}", permanent=True)


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
        projects_list = ["all-projects", *config.craft_projects]
        projects_file.write_text(json.dumps(projects_list, indent=2) + "\n")
        emit.progress(f"Wrote projects list to {projects_file}", permanent=True)


def get_median_age(dates: list[datetime] | None, date: datetime) -> int | None:
    """Get the median age in days of a list of dates from a reference date."""
    if dates:
        median_date = get_median_date(dates)
        return (date - median_date).days

    return None


def get_mean_date(dates: list[datetime]) -> datetime:
    """Get mean date from a list of datetimes."""
    reference = datetime(year=2000, month=1, day=1, tzinfo=UTC)
    return reference + sum([date - reference for date in dates], timedelta()) / len(
        dates,
    )


def get_median_date(dates: list[datetime]) -> datetime:
    """Get median date from a list of datetimes."""
    if len(dates) == 0:
        raise ValueError("Cannot get median date from an empty list")

    # if the list is even, average the middle two values
    if len(dates) % 2 == 0:
        return get_mean_date(dates[int(len(dates) / 2) - 1 : int(len(dates) / 2)])

    # if the list is odd, return the middle value
    return dates[int(len(dates) / 2)]
