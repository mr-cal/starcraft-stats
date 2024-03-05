"""Module for launchpad data collection."""

import argparse
import csv
from datetime import datetime
from pathlib import Path

from launchpadlib.launchpad import Launchpad  # type: ignore[import-untyped]

# This file relies heavily on dynamic features from launchpadlib that cause pyright
# to complain a lot. As such, we're disabling several pyright checkers for this file
# since in this case they generate more noise than utility.
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportOptionalSubscript=false
# pyright: reportIndexIssue=false


def get_launchpad_data(parsed_args: argparse.Namespace) -> None:
    """TODO."""
    project: str = parsed_args.project
    launchpad = Launchpad.login_anonymously("hello", "production")
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

    data = [datetime.now().strftime("%Y-%b-%d %H:%M:%S")]

    print(f"{project} bugs on launchpad")
    for status in statuses:
        bugs = launchpad_project.searchTasks(status=status)
        print(f"{len(bugs)} {status} bugs")
        data.append(str(len(bugs)))

    with Path(f"data/{project}-launchpad.csv").open("a", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(data)
