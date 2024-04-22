"""Module for github data collection."""

import argparse
import csv
import logging
import os
import pathlib
from datetime import datetime, timedelta, timezone
from functools import cached_property

from craft_application.models import CraftBaseModel
from github import Github

from .config import Config

logger = logging.getLogger(__name__)


class GithubIssue(CraftBaseModel):
    """Pydantic model for a github issue."""

    type: str
    date_opened: datetime
    date_closed: datetime | None

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

    issues: dict[int | str, GithubIssue] = {}


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

    :cvar name: The name of the project.
    :cvar owner: The owner of the project.
    :cvar __data: Data about the project's issues.
    :cvar data_file: The path to the local data file, written as yaml.
    :cvar csv_file: The path to the local csv file.
    """

    name: str
    owner: str
    __data: GithubIssues | None = None
    data_file: pathlib.Path
    csv_file: pathlib.Path

    def __init__(self, name: str, owner: str = "canonical") -> None:
        self.name = name
        self.owner = owner
        self.data_file = pathlib.Path(f"html/data/{name}-github.yaml")
        self.csv_file = pathlib.Path(f"html/data/{name}-github.csv")
        self.get_data()

    def __str__(self) -> str:
        """Return the project's name."""
        return self.name

    def get_data(self) -> GithubIssues:
        """Load a local data file containing Github issues for a project."""
        if self.__data:
            return self.__data

        if not self.data_file.exists():
            self.data_file.write_text("issues:")
            logger.info(f"Created {self.data_file}")

        data: GithubIssues = GithubIssues.from_yaml_file(self.data_file)
        if not data:
            data = GithubIssues(issues={})

        if not data.issues:
            data.issues = {}

        self.__data = data
        return data

    @cached_property
    def data(self) -> GithubIssues:
        """Get the data for the project."""
        return self.get_data()

    def update_data_from_github(self, github_api: Github) -> None:
        """Update a local data about issues from github."""
        logger.info(f"Collecting data for {self.name}")
        issues = github_api.get_repo(f"{self.owner}/{self.name}").get_issues(
            state="all",
        )

        for issue in issues:
            self.data.issues[issue.number] = GithubIssue(
                type="issue" if issue.pull_request is None else "pr",
                date_opened=issue.created_at,
                date_closed=issue.closed_at,
            )
            logger.debug(
                f"Collected issue {issue.number} {self.data.issues[issue.number]}",
            )

    def save_data_to_file(self) -> None:
        """Write data to a local file."""
        logger.debug(f"Writing data to {self.data_file}")

        self.data.to_yaml_file(self.data_file)
        logger.info(f"Wrote to {self.data_file}")

    def generate_csv(self) -> None:
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

        start_date = datetime(year=2021, month=1, day=1, tzinfo=timezone.utc)
        end_date = datetime.now(tz=timezone.utc)

        # iterate through each day from start_date to end_date
        logger.debug(f"Counting open issues and age for {self.name}")
        for date in [
            start_date + timedelta(days=i) for i in range((end_date - start_date).days)
        ]:
            open_issues = [
                issue for issue in self.data.issues.values() if issue.is_open(date)
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

        logger.debug(f"Calculating rolling averages for {self.name}")
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

        logger.debug(f"Writing data to {self.csv_file}")
        with self.csv_file.open("w", encoding="utf-8") as file:
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
        logger.info(f"Wrote to {self.csv_file}")


def get_issues(
    parsed_args: argparse.Namespace,  # noqa: ARG001 (unused argument)
    config: Config,
) -> None:
    """Collect data about issues and PRs for a set of github projects.

    Intermediate data about each issue in a project is stored in a yaml file.
    Then, this data is processed into a CSV file for visualization.
    """
    github_token = load_github_token()
    github_api = Github(github_token)

    # pseudo-project to aggregate data for all projects
    all_projects = GithubProject("all-projects")

    # iterate through all projects
    for project in config.craft_projects:
        github_project = GithubProject(project)
        github_project.update_data_from_github(github_api)
        github_project.save_data_to_file()
        github_project.generate_csv()

        for issue_number in github_project.data.issues:
            all_projects.data.issues[f"{github_project.name}-{str(issue_number)}"] = (
                github_project.data.issues[issue_number]
            )

    # generate csv and save data for all projects
    all_projects.generate_csv()
    all_projects.save_data_to_file()


def load_github_token() -> str:
    """Load a github token from the environment.

    Accept `STARCRAFT_GITHUB_TOKEN` because a personal fine-grained token has a max of
    5,000 API requests per hour whereas the `GITHUB_TOKEN` provided by GitHub Actions
    only allows 1,000 API requests per hour.
    """
    token = os.getenv("STARCRAFT_GITHUB_TOKEN")
    if token:
        logger.debug("Loaded STARCRAFT_GITHUB_TOKEN from environment")
        return token

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "Could not connect to github because environment "
            "variable GITHUB_TOKEN is not set",
        )
    return token


def get_median_age(dates: list[datetime] | None, date: datetime) -> int | None:
    """Get the median age in days of a list of dates from a reference date."""
    if dates:
        median_date = get_median_date(dates)
        return (date - median_date).days

    return None


def get_mean_date(dates: list[datetime]) -> datetime:
    """Get mean date from a list of datetimes."""
    reference = datetime(year=2000, month=1, day=1, tzinfo=timezone.utc)
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
