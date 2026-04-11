"""Module for launchpad data collection."""

import argparse
import pathlib
from datetime import UTC, datetime, timedelta

from craft_cli import BaseCommand, emit
from launchpadlib.launchpad import Launchpad

from .config import CONFIG_FILE, Config
from .const import CSV_START_DATE
from .issues import GithubProject, generate_all_projects_csv, get_median_age
from .models import IntermediateData, IntermediateDataPoint, IssueDataPoint
from .models.launchpad import LaunchpadBug, LaunchpadBugs, LaunchpadProjects

_ALL_STATUSES = [
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


class LaunchpadProject:
    """Collects, stores, and processes Launchpad bug data for a project.

    Per-bug records are stored in a shared YAML file. Data can be updated
    incrementally using Launchpad's modified_since filter, or bootstrapped
    with a full fetch.
    """

    data_file: pathlib.Path = pathlib.Path("html/data/issues-launchpad.yaml")

    def __init__(self) -> None:
        self._data = self._load_data()

    def _load_data(self) -> LaunchpadProjects:
        """Load bug data from the local YAML file, or return an empty store."""
        if self.data_file.exists():
            emit.progress(f"Loading data from {self.data_file}", permanent=True)
            return LaunchpadProjects.from_yaml_file(self.data_file)
        emit.message(f"Data file {self.data_file} does not exist.")
        return LaunchpadProjects(projects={})

    @property
    def data(self) -> LaunchpadProjects:
        """The in-memory bug data store."""
        return self._data

    @staticmethod
    def csv_file(project: str) -> pathlib.Path:
        """Get the CSV file path for a project."""
        return pathlib.Path(f"html/data/{project}-launchpad.csv")

    def _spread_refresh_dates(
        self,
        stored_bugs: dict,
        now: datetime,
        refresh_threshold: timedelta,
        refresh_interval_days: int,
    ) -> None:
        """Spread refresh_dates evenly across the refresh window after a bootstrap.

        This ensures future incremental runs only re-fetch a fraction of bugs
        each time rather than the entire dataset at once.
        """
        bug_ids = list(stored_bugs.keys())
        n = len(bug_ids)
        emit.debug(
            f"Spreading refresh_dates for {n} bugs over {refresh_interval_days} days"
        )
        for idx, bug_id in enumerate(bug_ids):
            fraction = idx / max(n, 1)
            spread_date = (
                now
                - refresh_threshold
                + timedelta(seconds=refresh_threshold.total_seconds() * fraction)
            )
            stored_bugs[bug_id] = LaunchpadBug(
                date_opened=stored_bugs[bug_id].date_opened,
                date_closed=stored_bugs[bug_id].date_closed,
                refresh_date=spread_date,
            )

    def _refresh_stale_bugs(
        self,
        lp_api: Launchpad,
        project: str,
        stored_bugs: dict,
        now: datetime,
        refresh_threshold: timedelta,
    ) -> int:
        """Re-fetch open bugs whose refresh_date has gone stale.

        Returns the number of bugs successfully refreshed from Launchpad.
        """
        stale_open = [
            bug_id
            for bug_id, bug in stored_bugs.items()
            if bug.date_closed is None and (now - bug.refresh_date) > refresh_threshold
        ]
        if not stale_open:
            return 0

        emit.progress(
            f"Re-fetching {len(stale_open)} stale open bugs for {project}...",
            permanent=True,
        )
        refreshed_count = 0
        for j, bug_id in enumerate(stale_open, start=1):
            try:
                lp_bug = lp_api.bugs[bug_id]
                lp_task = next(
                    (t for t in lp_bug.bug_tasks if t.bug_target_name == project),
                    None,
                )
                if lp_task:
                    stored_bugs[bug_id] = LaunchpadBug(
                        date_opened=lp_task.date_created,
                        date_closed=lp_task.date_closed,
                        refresh_date=now,
                    )
                    refreshed_count += 1
                else:
                    # Task no longer exists under this project; bump refresh_date so
                    # we don't retry on every subsequent run.
                    stored_bugs[bug_id] = LaunchpadBug(
                        date_opened=stored_bugs[bug_id].date_opened,
                        date_closed=stored_bugs[bug_id].date_closed,
                        refresh_date=now,
                    )
                emit.trace(
                    f"  stale [{j}/{len(stale_open)}] bug {bug_id}: "
                    f"closed={lp_task.date_closed.date() if lp_task and lp_task.date_closed else 'open'}"
                )
            except Exception as exc:  # noqa: BLE001
                emit.debug(f"Could not refresh bug {bug_id}: {exc}")
        return refreshed_count

    def update_data_from_launchpad(
        self,
        lp_api: Launchpad,
        project: str,
        refresh_interval_days: int = 7,
    ) -> None:
        """Update local bug data from Launchpad.

        Uses modified_since to fetch only recently changed bugs on subsequent
        runs. On first run (bootstrap), fetches all bugs.

        :param lp_api: An authenticated Launchpad API client.
        :param project: The Launchpad project name.
        :param refresh_interval_days: Days before re-fetching a stale open bug.
        """
        emit.progress(f"Collecting Launchpad data for {project}", permanent=True)

        if project not in self.data.projects:
            emit.debug(f"Creating new project entry for {project}")
            self.data.projects[project] = LaunchpadBugs(bugs={})

        stored_bugs = self.data.projects[project].bugs
        lp_project = lp_api.projects[project]
        now = datetime.now(tz=UTC)
        refresh_threshold = timedelta(days=refresh_interval_days)

        # Determine the oldest refresh_date to use as the modified_since cutoff.
        # If no bugs are stored yet, use epoch to trigger a full bootstrap fetch.
        is_bootstrap = not stored_bugs
        if is_bootstrap:
            oldest_refresh = datetime(1970, 1, 1, tzinfo=UTC)
            emit.progress(
                f"No existing data for {project} — starting full bootstrap fetch",
                permanent=True,
            )
        else:
            oldest_refresh = min(bug.refresh_date for bug in stored_bugs.values())
            emit.progress(
                f"Incremental fetch: {len(stored_bugs)} bugs already stored, "
                f"fetching changes since {oldest_refresh.date()}",
                permanent=True,
            )

        tasks = lp_project.searchTasks(
            status=_ALL_STATUSES,
            modified_since=oldest_refresh,
            order_by="datecreated",
        )
        total = tasks.total_size
        emit.progress(
            f"Fetching {total} bug tasks from Launchpad for {project}...",
            permanent=True,
        )

        new_count = 0
        updated_count = 0
        for i, task in enumerate(tasks, start=1):
            bug_id: int = task.bug.id
            is_new = bug_id not in stored_bugs
            stored_bugs[bug_id] = LaunchpadBug(
                date_opened=task.date_created,
                date_closed=task.date_closed,
                refresh_date=now,
            )
            if is_new:
                new_count += 1
            else:
                updated_count += 1
            emit.trace(
                f"  [{i}/{total}] bug {bug_id}: "
                f"opened={task.date_created.date()}, "
                f"closed={task.date_closed.date() if task.date_closed else 'open'}"
            )

        # After a bootstrap, spread refresh_dates evenly across the refresh window
        # so that future incremental runs only re-fetch a fraction of bugs each time.
        if is_bootstrap and stored_bugs:
            self._spread_refresh_dates(
                stored_bugs, now, refresh_threshold, refresh_interval_days
            )

        # Also re-fetch open bugs whose refresh_date has gone stale, in case
        # their status changed but wasn't caught by modified_since.
        refreshed_count = self._refresh_stale_bugs(
            lp_api, project, stored_bugs, now, refresh_threshold
        )

        emit.progress(
            f"Done — {new_count} new, {updated_count} updated, "
            f"{refreshed_count} stale-refreshed for {project}",
            permanent=True,
        )

    def save_data_to_file(self) -> None:
        """Write bug data to the local YAML file."""
        emit.progress(f"Writing data to {self.data_file}")
        self.data.to_yaml_file(self.data_file)
        emit.message(f"Wrote to {self.data_file}")

    def generate_csv(self, project: str) -> None:
        """Generate a per-day open-bugs CSV for a project.

        Uses the same day-by-day algorithm and IssueDataPoint CSV format as
        GithubProject.generate_csv(), so the frontend can reuse the same chart code.

        :param project: The Launchpad project name.
        """
        if project not in self.data.projects:
            emit.message(f"No data for {project}, skipping CSV generation")
            return

        start_date = CSV_START_DATE
        end_date = datetime.now(tz=UTC)

        bugs = list(self.data.projects[project].bugs.values())
        intermediate_data = IntermediateData()
        emit.progress(f"Counting open Launchpad bugs and age for {project}")

        for date in [
            start_date + timedelta(days=i) for i in range((end_date - start_date).days)
        ]:
            open_bugs = [bug for bug in bugs if bug.is_open(date)]
            closed_today = sum(
                1
                for bug in bugs
                if bug.date_closed is not None and bug.date_closed.date() == date.date()
            )
            intermediate_data.data.append(
                IntermediateDataPoint(
                    date=date.strftime("%Y-%b-%d"),
                    open_issues=len(open_bugs),
                    closed_issues=closed_today,
                    mean_age=get_median_age(
                        [bug.date_opened for bug in open_bugs],
                        date,
                    ),
                ),
            )

        csv_file = self.csv_file(project)
        emit.debug(f"Writing data to {csv_file}")
        IssueDataPoint.save_to_csv(intermediate_data.to_csv_models(), csv_file)
        emit.progress(f"Wrote to {csv_file}", permanent=True)


class GetLaunchpadDataCommand(BaseCommand):
    """Collect per-bug lifecycle data from Launchpad for configured projects."""

    name = "get-launchpad-data"
    help_msg = "Collect Launchpad bug data for configured projects"
    overview = "Collect Launchpad bug data for configured projects"
    common = True

    def run(
        self,
        parsed_args: argparse.Namespace,  # noqa: ARG002
    ) -> None:
        """Collect Launchpad bug data and regenerate all-projects CSV.

        :param parsed_args: parsed command line arguments
        """
        config = Config.from_yaml_file(CONFIG_FILE)
        lp = Launchpad.login_anonymously("starcraft-stats", "production")
        lp_project = LaunchpadProject()

        for project in config.launchpad_projects:
            lp_project.update_data_from_launchpad(
                lp, project, config.refresh_interval_days
            )
            lp_project.save_data_to_file()
            lp_project.generate_csv(project)

        # Regenerate the combined all-projects CSV and snapshot with fresh Launchpad data
        github_project = GithubProject()
        generate_all_projects_csv(github_project, lp_project.data)
        github_project.generate_snapshot(config.craft_projects, lp_project.data)
