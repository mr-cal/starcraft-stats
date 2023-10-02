#! /usr/bin/env python3

import argparse
import csv
from datetime import datetime, timedelta, timezone
import os
from typing import List, Union

from github import Github
from launchpadlib.launchpad import Launchpad


def get_launchpad_data(parsed_args: argparse.Namespace):
    project: str = parsed_args.project
    launchpad = Launchpad.login_anonymously('hello', 'production')
    launchpad_project = launchpad.projects[project]

    statuses = [
        "New",
        "Incomplete",
        "Opinion",
        "Invalid",
        "Won't Fix",
        "Expired",
        "Confirmed",
        "Triaged",
        "In Progress",
        "Fix Committed",
        "Fix Released",
        "Does Not Exist",
    ]

    data = [datetime.now().strftime('%Y-%b-%d %H:%M:%S')]

    print(f"{project} bugs on launchpad")
    for status in statuses:
        bugs = launchpad_project.searchTasks(status=status)
        print(f"{len(bugs)} {status} bugs")
        data.append(str(len(bugs)))

    with open(f"data/{project}-launchpad.csv", "a", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(data)


def get_mean_date(dates: List[datetime]) -> Union[datetime, str]:
    if not dates:
        return ""

    reference = datetime(year=2000, month=1, day=1, tzinfo=timezone.utc)
    return reference + sum([date - reference for date in dates], timedelta()) / len(dates)


def get_median_date(dates: List[datetime]) -> Union[datetime, str]:
    if not dates:
        return ""

    # if the list is even, average the middle two values
    if len(dates) % 2 == 0:
        return get_mean_date(dates[int(len(dates)/2)-1:int(len(dates)/2)])

    # if the list is odd, return the middle value
    return dates[int(len(dates)/2)]


def get_github_data(parsed_args: argparse.Namespace):
    user: str = parsed_args.user
    project: str = parsed_args.project
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        raise Exception(
            "Could not connect to github because envvar GITHUB_TOKEN is missing"
        )

    github_api = Github(github_token)

    data = [datetime.now().strftime("%Y-%b-%d %H:%M:%S")]

    open_issues = []
    open_prs = []

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
            get_mean_date(open_issues),
            get_median_date(open_issues),
            get_mean_date(open_prs),
            get_median_date(open_prs)
         ]
    )


    with open(f"data/{project}-github.csv", "a", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(data)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch starcraft data from github and launchpad."
    )

    subparsers = parser.add_subparsers(help="sub-command help")

    fetch_launchpad = subparsers.add_parser("launchpad", help="fetch data from launchpad")
    fetch_launchpad.set_defaults(func=get_launchpad_data)
    fetch_launchpad.add_argument(
        "project",
        help="github user project is under",
        metavar="user",
        type=str,
    )

    fetch_github = subparsers.add_parser("github", help="build and install a craft application")
    fetch_github.set_defaults(func=get_github_data)
    fetch_github.add_argument(
        "user",
        help="github user project is under",
        metavar="user",
        type=str,
    )
    fetch_github.add_argument(
        "project",
        help="github project",
        metavar="project",
        type=str,
    )

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
