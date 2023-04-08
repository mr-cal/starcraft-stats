#! /usr/bin/env python3

import csv
from datetime import datetime, timedelta
import os
from typing import List, Union

from github import Github
from launchpadlib.launchpad import Launchpad


def get_launchpad_data():
    launchpad = Launchpad.login_anonymously('hello', 'production')
    snapcraft = launchpad.projects["snapcraft"]

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

    print("snapcraft bugs on launchpad")
    for status in statuses:
        bugs = snapcraft.searchTasks(status=status)
        print(f"{len(bugs)} {status} bugs")
        data.append(str(len(bugs)))

    with open("data/snapcraft-launchpad.csv", "a", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(data)


def get_mean_date(dates: List[datetime]) -> Union[datetime, str]:
    if not dates:
        return ""

    reference = datetime(2000, 1, 1)
    return reference + sum([date - reference for date in dates], timedelta()) / len(dates)


def get_median_date(dates: List[datetime]) -> Union[datetime, str]:
    if not dates:
        return ""

    # if the list is even, average the middle two values
    if len(dates) % 2 == 0:
        return get_mean_date(dates[int(len(dates)/2)-1:int(len(dates)/2)])

    # if the list is odd, return the middle value
    return dates[int(len(dates)/2)]


def get_github_data(user: str, project: str):
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
    get_launchpad_data()
    get_github_data("canonical", "charmcraft")
    get_github_data("canonical", "craft-archives")
    get_github_data("canonical", "craft-cli")
    get_github_data("canonical", "craft-grammar")
    get_github_data("canonical", "craft-parts")
    get_github_data("canonical", "craft-providers")
    get_github_data("canonical", "craft-store")
    get_github_data("canonical", "rockcraft")
    get_github_data("snapcore", "snapcraft")

if __name__ == "__main__":
    main()
