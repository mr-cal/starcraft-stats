"""Module for github data collection."""

import argparse
import csv
import os
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Union
from craft_application.models import CraftBaseModel

from github import Github


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
        return self.date_opened < date and (self.date_closed is None or self.date_closed > date)


class GithubIssues(CraftBaseModel):
    """Pydantic model for a collection of github issues."""

    issues: Dict[int | str, GithubIssue | None] | None = {}


class GithubProject:
    """Class for a github project.

    :cvar name: The name of the project.
    :cvar owner: The owner of the project.
    :cvar data: Data about the project's issues.
    :cvar data_file: The path to the local data file, written as yaml.
    :cvar csv_file: The path to the local csv file.
    """

    name: str
    owner: str
    data: GithubIssues | None = None
    data_file: Path
    csv_file: Path

    def __init__(self, name: str, owner: str = "canonical") -> None:
        self.name = name
        self.owner = owner
        self.data_file = Path(f"html/data/{name}-github.yaml")
        self.csv_file = Path(f"html/data/{name}-github.csv")

    def __str__(self) -> str:
        """Return the project's name."""
        return self.name

    def load_data(self) -> None:
        """Load a local data file containing Github issues for a project."""
        if self.data:
            return

        if not self.data_file.exists():
            self.data_file.write_text("issues:")
            logger.info(f"Created {self.data_file}")

        data: GithubIssues = GithubIssues.from_yaml_file(self.data_file)
        if not data:
            data = GithubIssues(issues={})

        if not data.issues:
            data.issues = {}

        self.data = data

    def update_local_data(self, github_api: Github) -> None:
        """Update a local data about issues from github."""
        logger.info(f"Collecting data for {self.name}")
        issues = github_api.get_repo(f"{self.owner}/{self.name}").get_issues(
            state="all")

        for issue in issues:
            self.data.issues[issue.number] = GithubIssue(
                type="issue" if issue.pull_request is None else "pr",
                date_opened=issue.created_at,
                date_closed=issue.closed_at,
            )
            logger.debug(f"Collected issue {issue.number} {self.data.issues[issue.number]}")

        self.data.to_yaml_file(self.data_file)
        logger.info(f"Wrote to {self.data_file}")

    def generate_csv(self) -> None:
        """Generate a CSV file from a GithubIssues object.

        Formatted as:
        | date       | open issues | mean age (days) |
        | ---------- | ----------- | --------------- |
        | 2021-01-01 | 10          | 20              |
        | ...        | ...         | ...             |
        """
        logger.debug(f"Writing data to {self.csv_file}")
        with self.csv_file.open("w", encoding="utf-8") as file:
            writer = csv.writer(file, lineterminator="\n")
            writer.writerow(["date", "issues", "age"])

            start_date = datetime(year=2021, month=1, day=1, tzinfo=timezone.utc)
            end_date = datetime.now(tz=timezone.utc)

            # iterate through each day from start_date to end_date
            for date in [start_date + timedelta(days=i) for i in range((end_date - start_date).days)]:
                logger.debug(f"Calculating issues for {date}")
                open_issues = [
                    issue for issue in self.data.issues.values() if issue.is_open(date)
                ]
                mean_age = get_median_age([issue.date_opened for issue in open_issues], date)
                logger.debug(
                    f"Date: {date.strftime('%Y-%m-%d')}, open issues: {len(open_issues)}, median age: {mean_age} days"
                )
                writer.writerow([date.strftime("%Y-%m-%d"), len(open_issues), mean_age])

            logger.info(f"Wrote to {self.csv_file}")


# TODO
# ----
# rolling averages
# make "all-projects" project cleaner
# better sub-commands and arguments to not always fetch data
# retry on 404?
# specify which libraries to load

CRAFT_PROJECTS = [
    GithubProject("charmcraft"),
    #GithubProject("craft-application"),
    #GithubProject("craft-archives"),
    #GithubProject("craft-cli"),
    #GithubProject("craft-grammar"),
    #GithubProject("craft-parts"),
    #GithubProject("craft-providers"),
    #GithubProject("craft-store"),
    #GithubProject("rockcraft"),
    #GithubProject("snapcraft"),
    #GithubProject("starbase"),
]


def collect_github_data(parsed_args: argparse.Namespace) -> None:
    """Collect data about issues and PRs for a set of github projects.

    Intermediate data about each issue in a project is stored in a yaml file.
    Then, this data is processed into a CSV file for visualization.
    """
    github_token = load_github_token()
    github_api = Github(github_token)

    # pseudo-project to aggregate data for all projects
    all_projects = GithubProject("all-projects")
    all_projects.load_data()

    for project in CRAFT_PROJECTS:
        project.load_data()
        project.update_local_data(github_api)
        project.generate_csv()

        for issue_number in project.data.issues:
            all_projects.data.issues[f"{project.name}-{str(issue_number)}"] = project.data.issues[issue_number]


    all_projects.data.to_yaml_file(all_projects.data_file)
    all_projects.generate_csv()
    logger.info(f"Wrote all project data to {all_projects.data_file}")


def load_github_token() -> str:
    """Load a github token from the environment."""
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        raise RuntimeError(
            "Could not connect to github because environment "
            "variable GITHUB_TOKEN is missing",
        )
    logger.debug("Loaded GITHUB_TOKEN from environment")
    return github_token


def get_median_age(dates: List[datetime] | None, date: datetime) -> int | None:
    """Get the median age in days of a list of dates from a reference date."""
    if dates:
        median_date = get_median_date(dates)
        return (date - median_date).days

    return None


def get_mean_date(dates: List[datetime]) -> datetime:
    """Get mean date from a list of datetimes."""
    reference = datetime(year=2000, month=1, day=1, tzinfo=timezone.utc)
    return reference + sum([date - reference for date in dates], timedelta()) / len(dates)


def get_median_date(dates: List[datetime]) -> Union[datetime, str]:
    """Get median date from a list of datetimes."""
    if not dates:
        return ""

    # if the list is even, average the middle two values
    if len(dates) % 2 == 0:
        return get_mean_date(dates[int(len(dates) / 2) - 1: int(len(dates) / 2)])

    # if the list is odd, return the middle value
    return dates[int(len(dates) / 2)]
