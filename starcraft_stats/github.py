"""Module for github data collection."""

import argparse
import csv
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Union

from github import Github


def get_mean_date(dates: List[datetime]) -> Union[datetime, str]:
    """TODO."""
    if not dates:
        return ""

    reference = datetime(year=2000, month=1, day=1, tzinfo=timezone.utc)
    return reference + sum([date - reference for date in dates], timedelta()) / len(
        dates,
    )


def get_median_date(dates: List[datetime]) -> Union[datetime, str]:
    """TODO."""
    if not dates:
        return ""

    # if the list is even, average the middle two values
    if len(dates) % 2 == 0:
        return get_mean_date(dates[int(len(dates) / 2) - 1 : int(len(dates) / 2)])

    # if the list is odd, return the middle value
    return dates[int(len(dates) / 2)]


def get_github_data(parsed_args: argparse.Namespace) -> None:
    """Get github data for a project."""
    user: str = parsed_args.user
    project: str = parsed_args.project
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        raise RuntimeError(
            "Could not connect to github because envvar GITHUB_TOKEN is missing",
        )

    github_api = Github(github_token)

    data = [datetime.now().strftime("%Y-%b-%d %H:%M:%S")]

    open_issues: List[datetime] = []
    open_prs: List[datetime] = []

    issues = github_api.get_repo(f"{user}/{project}").get_issues(state="open")
    for issue in issues:
        if issue.pull_request:
            open_prs.append(issue.created_at)
        else:
            open_issues.append(issue.created_at)

    data.extend(
        [
            str(len(open_prs)),
            str(len(open_issues)),
            str(get_mean_date(open_issues)),
            str(get_median_date(open_issues)),
            str(get_mean_date(open_prs)),
            str(get_median_date(open_prs)),
        ],
    )

    with Path(f"data/{project}-github.csv").open("a", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(data)
