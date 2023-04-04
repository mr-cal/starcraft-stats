#! /usr/bin/env python3

import csv
from datetime import datetime
import os

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


def get_github_data(user: str, project: str):
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        raise Exception(
            "Could not connect to github because envvar GITHUB_TOKEN is missing"
        )

    github_api = Github(github_token)

    data = [datetime.now().strftime("%Y-%b-%d %H:%M:%S")]

    total_issues = github_api.get_repo(f"{user}/{project}").get_issues(state="open").totalCount
    prs = github_api.get_repo(f"{user}/{project}").get_pulls(state="open").totalCount
    open_issues = total_issues - prs

    data.extend([str(prs), str(open_issues)])

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
