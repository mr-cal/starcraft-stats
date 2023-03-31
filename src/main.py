#! /usr/bin/env python3

import csv
from datetime import datetime
import json
from launchpadlib.launchpad import Launchpad

def main():
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

    with open("data/snapcraft-bugs.csv", "a") as file:
        fields = ["Date"] + statuses
        writer = csv.writer(file)
        writer.writerow(data)

if __name__ == "__main__":
    main()
