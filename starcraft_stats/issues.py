"""Module for github data collection."""

import argparse
import csv
import os
import pathlib
from datetime import UTC, datetime, timedelta
from functools import cached_property

from craft_application.models import CraftBaseModel
from craft_cli import BaseCommand, emit
from github import Github

from .config import CONFIG_FILE, Config


class GithubIssue(CraftBaseModel):
    """Pydantic model for a github issue."""

    type: str
    """The type of issue, either 'issue' or 'pr'."""

    date_opened: datetime
    """The date the issue was opened."""

    date_closed: datetime | None
    """The date the issue was closed, if applicable."""

    def __str__(self) -> str:
        """Return the issue as a string."""
        date_closed = f" closed: {self.date_closed}" if self.date_closed else ""
        return f"type: {self.type} opened: {self.date_opened}{date_closed}"

    def is_open(self, date: datetime) -> bool:
        """Check if an issue was open on a particular date."""
        return self.date_opened < date and (
            self.date_closed is None or self.date_closed > date
        )


class GithubIssues(CraftBaseModel):
    """Pydantic model for a collection of github issues."""

    issues: dict[int, GithubIssue] = {}
    """A dictionary of issues, indexed by issue number."""


class Projects(CraftBaseModel):
    """Pydantic model for a collection of github projects."""

    projects: dict[str, GithubIssues] = {}
    """A dictionary of projects, indexed by project name."""


class IntermediateDataPoint(CraftBaseModel):
    """Intermediate datapoint about issues for a github project."""

    date: str
    open_issues: int
    open_issues_avg: int | None = None
    mean_age: int | None


class IntermediateData(CraftBaseModel):
    """Intermediate data about issues for a github project."""

    data: list[IntermediateDataPoint] = []


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

    def update_data_from_github(self, github_api: Github, project: str) -> None:
        """Update a local data about issues from github."""
        emit.progress(f"Collecting data for {self.owner}/{project}", permanent=True)
        issues = github_api.get_repo(f"{self.owner}/{project}").get_issues(
            state="all",
        )

        if project not in self.data.projects:
            emit.debug(f"Creating new project in data file {project}")
            self.data.projects[project] = GithubIssues(issues={})

        for issue in issues:
            self.data.projects[project].issues[int(issue.number)] = GithubIssue(
                type="issue" if issue.pull_request is None else "pr",
                date_opened=issue.created_at,
                date_closed=issue.closed_at,
            )
            emit.debug(
                f"Collected issue {issue.number} {self.data.projects[project].issues[issue.number]}",
            )
        emit.progress(
            f"Collected {len(self.data.projects[project].issues)} issues for {project}"
        )

    def save_data_to_file(self) -> None:
        """Write data to a local file."""
        emit.progress(f"Writing data to {self.data_file}")

        self.data.to_yaml_file(self.data_file)
        emit.message(f"Wrote to {self.data_file}")

    def generate_csv(self, project: str) -> None:
        """Generate a CSV file from a GithubIssues object.

        Steps:
        1. Generate an intermediate data structure containing the date, open issues, and mean age.
        2. Compute rolling averages for open issues and mean age and add to data structure.
        3. Write the data to a CSV file.

        Rolling averages are done for a smoother visualization.

        Data is organized as:
        | date       | open issues | open issues average | mean age  | mean age average |
        | ---------- | ----------- | ------------------- | --------- | ---------------- |
        | 2021-01-01 | 10          | 10                  | 20        | 20               |
        | ...        | ...         | ...                 | ...       | ...              |
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

        emit.progress(f"Calculating rolling averages for {project}")
        window_size = 4
        for entry in intermediate_data.data:
            # compute rolling averages
            start_date_index = max(
                0,
                intermediate_data.data.index(entry) - window_size + 1,
            )
            window_data = intermediate_data.data[
                start_date_index : intermediate_data.data.index(entry) + 1
            ]
            average_open_issues = sum(
                entry.open_issues for entry in window_data
            ) // len(window_data)
            entry.open_issues_avg = average_open_issues

        csv_file = self.csv_file(str(project))
        emit.debug(f"Writing data to {csv_file}")
        with csv_file.open("w", encoding="utf-8") as file:
            writer = csv.writer(file, lineterminator="\n")
            writer.writerow(["date", "issues", "issues_avg", "age"])
            for entry in intermediate_data.data:
                writer.writerow(
                    [
                        entry.date,
                        entry.open_issues,
                        entry.open_issues_avg,
                        entry.mean_age,
                    ],
                )
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
            github_project.update_data_from_github(github_api, project)
            github_project.save_data_to_file()
            github_project.generate_csv(project)

        # generate csv and save data for all projects
        github_project.generate_csv("all")


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
