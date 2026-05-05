"""Module for scheduling refresh dates across issues."""

import argparse
import math
import pathlib
from datetime import UTC, datetime, timedelta

from craft_cli import BaseCommand, emit

from .config import CONFIG_FILE, Config
from .models import Projects


class ScheduleRefreshCommand(BaseCommand):
    """Distribute refresh dates for all GitHub issues evenly over the next refresh interval.

    By default, all issues share a refresh_date near the last time they were fetched,
    meaning they all expire at roughly the same time and cause a burst of API calls.
    This command spreads the refresh_date values so that approximately
    ``total_issues / refresh_interval_days`` issues expire each day over the next
    ``refresh_interval_days`` days.
    """

    name = "schedule-refresh"
    help_msg = "Distribute issue refresh dates evenly over the refresh interval"
    overview = (
        "Distribute issue refresh dates evenly over the next refresh-interval-days days.\n\n"
        "Running this command once after a full data fetch ensures that subsequent\n"
        "get-issues runs each refresh only a fraction of the total issues, rather\n"
        "than re-fetching everything at once."
    )
    common = True

    def run(
        self,
        parsed_args: argparse.Namespace,  # noqa: ARG002
    ) -> None:
        """Distribute refresh dates across all issues in the data file."""
        config = Config.from_yaml_file(CONFIG_FILE)
        data_file = pathlib.Path("html/data/issues-github.yaml")

        if not data_file.exists():
            raise RuntimeError(
                f"Data file {data_file} does not exist. "
                "Run 'get-issues' first to populate it."
            )

        emit.progress(f"Loading data from {data_file}", permanent=True)
        projects = Projects.from_yaml_file(data_file)

        # Collect all (project_name, issue_number) pairs
        all_issues: list[tuple[str, int]] = [
            (project_name, issue_num)
            for project_name, project_issues in projects.projects.items()
            for issue_num in project_issues.issues
        ]

        total = len(all_issues)
        if total == 0:
            emit.message("No issues found in data file — nothing to schedule.")
            return

        interval = config.refresh_interval_days
        now = datetime.now(tz=UTC)

        emit.progress(
            f"Distributing {total} issues across {interval} days", permanent=True
        )

        for i, (project_name, issue_num) in enumerate(all_issues):
            # Spread expiry evenly: issue i expires in ceil((i+1)/total * interval) days.
            days_until_expire = math.ceil((i + 1) / total * interval)
            # refresh_date that will cause the issue to expire exactly that many days from now
            new_refresh_date = now - timedelta(days=interval - days_until_expire)
            projects.projects[project_name].issues[
                issue_num
            ].refresh_date = new_refresh_date

        emit.progress(f"Writing updated refresh dates to {data_file}", permanent=True)
        projects.to_yaml_file(data_file)
        emit.message(
            f"Scheduled {total} issues across {interval} days "
            f"(~{total // interval} issues expiring per day)."
        )
