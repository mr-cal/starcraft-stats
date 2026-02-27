"""Module for launchpad data collection."""

import argparse
import pathlib
from datetime import datetime

from craft_cli import BaseCommand, emit
from launchpadlib.launchpad import Launchpad

from .models import LaunchpadDataPoint

# Maps Launchpad status display names to LaunchpadDataPoint field names
_STATUS_FIELD_MAP: dict[str, str] = {
    "New": "new",
    "Incomplete": "incomplete",
    "Opinion": "opinion",
    "Invalid": "invalid",
    "Won't Fix": "wont_fix",
    "Expired": "expired",
    "Confirmed": "confirmed",
    "Triaged": "triaged",
    "In Progress": "in_progress",
    "Fix Committed": "fix_committed",
    "Fix Released": "fix_released",
    "Does Not Exist": "does_not_exist",
}


class GetLaunchpadDataCommand(BaseCommand):
    """Get launchpad data for a project."""

    name = "get-launchpad-data"
    help_msg = "Collect launchpad data for a project"
    overview = "Collect launchpad data for a project"
    common = True

    def run(
        self,
        parsed_args: argparse.Namespace,
    ) -> None:
        """Collect launchpad data for a project."""
        project: str = parsed_args.project
        launchpad = Launchpad.login_anonymously("hello", "production")
        launchpad_project = launchpad.projects[project]

        data_dict: dict[str, str | int] = {
            "timestamp": datetime.now().strftime("%Y-%b-%d %H:%M:%S"),
        }

        emit.message(f"{project} bugs on launchpad")
        for status, field_name in _STATUS_FIELD_MAP.items():
            bugs = launchpad_project.searchTasks(status=status)
            count = len(bugs)
            emit.message(f"{count} {status} bugs")
            data_dict[field_name] = count

        data_point = LaunchpadDataPoint(**data_dict)  # type: ignore[arg-type]
        csv_file = pathlib.Path(f"data/{project}-launchpad.csv")
        LaunchpadDataPoint.save_to_csv([data_point], csv_file, append=True)
