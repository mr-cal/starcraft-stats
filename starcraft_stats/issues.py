"""Module for github data collection."""

import argparse
import json
import os
import pathlib
from datetime import UTC, datetime, timedelta

from craft_cli import BaseCommand, emit
from github import Github, GithubException
from github.Issue import Issue as GithubApiIssue

from .config import CONFIG_FILE, Config
from .const import CSV_START_DATE
from .models import (
    GithubIssue,
    GithubIssues,
    IntermediateData,
    IntermediateDataPoint,
    IssueDataPoint,
    LaunchpadBug,
    LaunchpadProjects,
    Projects,
    ProjectsData,
    SnapshotMetrics,
)


class GithubProject:
    """Class for a github project.

    This class can load data from a file, update that data from github,
    and save the data to a file.

    It also generates a CSV file ready for visualization.

    :cvar owner: The owner of the project.
    :cvar data_file: The path to the shared local data file, written as yaml.
    """

    owner: str
    data_file: pathlib.Path

    def __init__(self, owner: str = "canonical") -> None:
        self.owner = owner
        self.data_file = pathlib.Path("html/data/issues-github.yaml")
        self._data = self._load_data()

    def _load_data(self) -> Projects:
        """Load issue data from the local YAML file, or return an empty store."""
        if self.data_file.exists():
            emit.progress(f"Loading data from {self.data_file}", permanent=True)
            return Projects.from_yaml_file(self.data_file)
        emit.message(f"Data file {self.data_file} does not exist.")
        return Projects(projects={})

    @property
    def data(self) -> Projects:
        """The in-memory issue data store."""
        return self._data

    @staticmethod
    def csv_file(project: str) -> pathlib.Path:
        """Get the csv file for a project."""
        if project == "all":
            return pathlib.Path("html/data/all-projects-github.csv")
        return pathlib.Path(f"html/data/{project}-github.csv")

    @staticmethod
    def _issue_from_api(api_issue: GithubApiIssue, now: datetime) -> GithubIssue:
        """Construct a GithubIssue from a PyGithub issue object."""
        return GithubIssue(
            type="issue" if api_issue.pull_request is None else "pr",
            date_opened=api_issue.created_at,
            date_closed=api_issue.closed_at,
            refresh_date=now,
            opened_by=api_issue.user.login if api_issue.user else None,
        )

    def update_data_from_github(
        self, github_api: Github, project: str, refresh_interval_days: int = 7
    ) -> None:
        """Update local data about issues from github.

        Only fetches issues that haven't been refreshed in the specified interval,
        and always checks for new issues.

        :param github_api: GitHub API client
        :param project: Project name
        :param refresh_interval_days: Number of days before refreshing an issue
        """
        emit.progress(f"Collecting data for {self.owner}/{project}", permanent=True)

        # Initialize project if it doesn't exist
        if project not in self.data.projects:
            emit.debug(f"Creating new project in data file {project}")
            self.data.projects[project] = GithubIssues(issues={})

        now = datetime.now(tz=UTC)
        refresh_threshold = timedelta(days=refresh_interval_days)
        repo = github_api.get_repo(f"{self.owner}/{project}")

        # Find issues that need refreshing (haven't been updated in threshold days)
        issues_to_refresh = [
            issue_num
            for issue_num, issue in self.data.projects[project].issues.items()
            if (now - issue.refresh_date) > refresh_threshold
        ]
        total_to_refresh = len(issues_to_refresh)
        emit.debug(f"[{project}] Found {total_to_refresh} existing issues to refresh")

        # Refresh stale issues
        for i, issue_num in enumerate(issues_to_refresh):
            emit.trace(
                f"[{project}] Refreshing issue {issue_num} ({i + 1}/{total_to_refresh})"
            )
            try:
                api_issue = repo.get_issue(number=issue_num)
                self.data.projects[project].issues[issue_num] = self._issue_from_api(
                    api_issue, now
                )
                emit.trace(f"[{project}] Refreshed issue {issue_num}")
            except (GithubException, RuntimeError) as e:
                emit.debug(f"[{project}] Could not refresh issue {issue_num}: {e}")

        # Save after stale-refresh so a crash in new-issue discovery doesn't
        # lose the refresh_date updates we just made
        self.save_data_to_file()

        # Check for new issues starting from the highest known issue number
        max_issue_num = max(self.data.projects[project].issues.keys(), default=0)
        emit.debug(f"[{project}] Highest existing issue number: {max_issue_num}")

        new_issues_found = 0
        next_issue_num = max_issue_num + 1
        consecutive_not_found = 0
        max_consecutive_not_found = 5  # Stop after 5 consecutive missing issues

        while consecutive_not_found < max_consecutive_not_found:
            emit.trace(f"[{project}] Checking new issue {next_issue_num}")
            try:
                api_issue = repo.get_issue(number=next_issue_num)
                self.data.projects[project].issues[next_issue_num] = (
                    self._issue_from_api(api_issue, now)
                )
                emit.trace(f"[{project}] Found new issue {next_issue_num}")
                new_issues_found += 1
                consecutive_not_found = 0
            except (GithubException, RuntimeError) as e:
                emit.trace(f"[{project}] Issue {next_issue_num} not found: {e}")
                consecutive_not_found += 1

            next_issue_num += 1

        emit.progress(
            f"Refreshed {len(issues_to_refresh)} issues, found {new_issues_found} new issues for {project}",
            permanent=True,
        )

    def save_data_to_file(self) -> None:
        """Write data to a local file."""
        emit.progress(f"Writing data to {self.data_file}")
        self.data.to_yaml_file(self.data_file)
        emit.message(f"Wrote to {self.data_file}")

    def generate_csv(self, project: str, maintainers: set[str] | None = None) -> None:
        """Generate a CSV file from issue data.

        Iterates through each day from the start date to today, counts open issues
        and computes median age, then writes the results to a CSV file.

        Data is organized as:
        | date       | open issues | closed | age | nm_issues | nm_closed | nm_age |
        | ---------- | ----------- | ------ | --- | --------- | --------- | ------ |
        | 2021-01-01 | 10          | 2      | 20  | 8         | 1         | 15     |
        | ...        | ...         | ...    | ... | ...       | ...       | ...    |

        :param project: The project name, or "all" for all projects combined.
        :param maintainers: Set of maintainer GitHub usernames. Issues opened by these
            users are excluded from the ``nm_*`` (non-maintainer) columns.
        """
        if project == "all":
            issues = [
                issue
                for proj in self.data.projects.values()
                for issue in proj.issues.values()
            ]
        else:
            issues = list(self.data.projects[project].issues.values())

        _generate_issue_csv(
            issues, self.csv_file(str(project)), project, maintainers or set()
        )

    def generate_snapshot(
        self,
        projects: list[str],
        launchpad_data: LaunchpadProjects | None = None,
        maintainers: set[str] | None = None,
    ) -> None:
        """Generate a point-in-time snapshot JSON for the comparison charts.

        For each project, computes open issues, open PRs, median age of open issues,
        median age of open PRs, and issues/PRs closed in the last year. Non-maintainer
        (``nm_*``) variants of each metric are also included.

        :param projects: Ordered list of project names to include.
        :param launchpad_data: Optional Launchpad bug data to include as extra entries.
        :param maintainers: Set of maintainer GitHub usernames used to separate
            maintainer activity from non-maintainer activity in the ``nm_*`` fields.
            Launchpad bugs are always treated as non-maintainer.
        """
        maintainers = maintainers or set()
        now = datetime.now(tz=UTC)
        one_year_ago = now - timedelta(days=365)

        snapshot: dict[str, SnapshotMetrics] = {}
        for project in projects:
            if project not in self.data.projects:
                continue
            snapshot[project] = _compute_snapshot_metrics(
                gh_issues=list(self.data.projects[project].issues.values()),
                lp_bugs=[],
                now=now,
                one_year_ago=one_year_ago,
                maintainers=maintainers,
            )

        if launchpad_data:
            for lp_project, lp_bugs in launchpad_data.projects.items():
                snapshot[f"{lp_project} (launchpad)"] = _compute_snapshot_metrics(
                    gh_issues=[],
                    lp_bugs=list(lp_bugs.bugs.values()),
                    now=now,
                    one_year_ago=one_year_ago,
                    maintainers=maintainers,
                )

        # "all-projects" aggregates GitHub + Launchpad using the same raw-data
        # methodology as generate_all_projects_csv so snapshot matches line charts.
        all_gh = [
            issue
            for proj in self.data.projects.values()
            for issue in proj.issues.values()
        ]
        all_lp = (
            [
                bug
                for proj in launchpad_data.projects.values()
                for bug in proj.bugs.values()
            ]
            if launchpad_data
            else []
        )
        snapshot["all-projects"] = _compute_snapshot_metrics(
            gh_issues=all_gh,
            lp_bugs=all_lp,
            now=now,
            one_year_ago=one_year_ago,
            maintainers=maintainers,
        )

        snapshot_file = pathlib.Path("html/data/snapshot.json")
        snapshot_file.write_text(
            json.dumps({k: v.model_dump() for k, v in snapshot.items()}, indent=2)
            + "\n"
        )
        emit.progress(f"Wrote snapshot to {snapshot_file}", permanent=True)


def load_github_token() -> str:
    """Load a github token from the environment.

    Accept `STARCRAFT_GITHUB_TOKEN` because a personal fine-grained token has a max of
    5,000 API requests per hour whereas the `GITHUB_TOKEN` provided by GitHub Actions
    only allows 1,000 API requests per hour.
    """
    token = os.getenv("STARCRAFT_GITHUB_TOKEN")
    if token:
        emit.debug("Loaded STARCRAFT_GITHUB_TOKEN from environment")
        return token

    token = os.getenv("GITHUB_TOKEN")
    if token:
        emit.debug("Loaded GITHUB_TOKEN from environment")
    else:
        raise RuntimeError(
            "Could not connect to github because environment "
            "variable GITHUB_TOKEN is not set",
        )
    return token


class GetIssuesCommand(BaseCommand):
    """Collect data about issues and PRs for a set of github projects.

    Intermediate data about each issue in a project is stored in a yaml file.
    Then, this data is processed into a CSV file for visualization.
    """

    name = "get-issues"
    help_msg = "Collect data on open issues from github"
    overview = "Collect data on open issues from github"
    common = True

    def run(
        self,
        parsed_args: argparse.Namespace,  # noqa: ARG002 (Unused method argument)
    ) -> None:
        """Collect data on open issues from github.

        :param parsed_args: parsed command line arguments
        """
        config = Config.from_toml_file(CONFIG_FILE)
        maintainers = set(config.maintainers)
        github_token = load_github_token()
        github_api = Github(github_token)
        github_project = GithubProject()

        # iterate through all projects
        for project in config.craft_projects:
            github_project.update_data_from_github(
                github_api, project, config.refresh_interval_days
            )
            github_project.save_data_to_file()
            github_project.generate_csv(project, maintainers)

        # generate csv for all projects combined (Launchpad data loaded separately)
        launchpad_data = (
            LaunchpadProjects.from_yaml_file(
                pathlib.Path("html/data/issues-launchpad.yaml")
            )
            if pathlib.Path("html/data/issues-launchpad.yaml").exists()
            else LaunchpadProjects()
        )
        generate_all_projects_csv(github_project, launchpad_data, maintainers)

        # write the project list for the frontend
        projects_file = pathlib.Path("html/data/projects.json")
        known = set(config.craft_applications) | set(config.craft_libraries)
        other_projects = [p for p in config.craft_projects if p not in known]
        launchpad_with_suffix = [f"{p} (launchpad)" for p in config.launchpad_projects]
        projects_data = ProjectsData(
            applications=config.craft_applications,
            libraries=config.craft_libraries,
            other=other_projects,
            launchpad=config.launchpad_projects,
            # craft-projects defines display order; launchpad appended at the end.
            ordered=[*config.craft_projects, *launchpad_with_suffix],
        )
        projects_file.write_text(projects_data.model_dump_json(indent=2) + "\n")
        emit.progress(f"Wrote projects list to {projects_file}", permanent=True)

        # write the snapshot for the comparison charts
        github_project.generate_snapshot(
            config.craft_projects, launchpad_data, maintainers
        )


def generate_all_projects_csv(
    github_project: "GithubProject",
    launchpad_data: LaunchpadProjects,
    maintainers: set[str] | None = None,
) -> None:
    """Generate the all-projects combined open-issues CSV.

    Counts GitHub open issues and Launchpad open bugs per day.
    Both share the is_open(date) interface so no special-casing is needed.

    :param github_project: GitHub project data.
    :param launchpad_data: Launchpad bug data.
    :param maintainers: Set of maintainer GitHub usernames. Launchpad bugs are always
        treated as non-maintainer.
    """
    github_issues = [
        issue
        for proj in github_project.data.projects.values()
        for issue in proj.issues.values()
    ]
    launchpad_bugs = [
        bug for proj in launchpad_data.projects.values() for bug in proj.bugs.values()
    ]
    _generate_issue_csv(
        github_issues + launchpad_bugs,
        GithubProject.csv_file("all"),
        "all projects",
        maintainers or set(),
    )


def _compute_snapshot_metrics(
    gh_issues: list[GithubIssue],
    lp_bugs: list[LaunchpadBug],
    now: datetime,
    one_year_ago: datetime,
    maintainers: set[str],
) -> SnapshotMetrics:
    """Compute all snapshot metrics for a combined set of GitHub issues and Launchpad bugs.

    Works for a single GitHub project (``lp_bugs=[]``), a single Launchpad project
    (``gh_issues=[]``), or the all-projects aggregate (both populated).  Launchpad bugs
    have no ``type`` or ``opened_by`` so they are always counted as non-maintainer
    issues (never PRs).

    :param gh_issues: GitHub issues/PRs for the project(s).
    :param lp_bugs: Launchpad bugs for the project(s). Always treated as nm issues.
    :param now: Reference datetime for open/closed checks.
    :param one_year_ago: Lower bound for the "closed in last year" counts.
    :param maintainers: Set of maintainer GitHub usernames.
    :returns: Dict matching the snapshot JSON schema for one project entry.
    """
    open_issues = [i for i in gh_issues if i.type == "issue" and i.is_open(now)] + [
        b for b in lp_bugs if b.is_open(now)
    ]
    open_prs = [i for i in gh_issues if i.type == "pr" and i.is_open(now)]
    nm_open_issues = [
        i
        for i in gh_issues
        if i.type == "issue" and i.is_open(now) and not _is_maintainer(i, maintainers)
    ] + [b for b in lp_bugs if b.is_open(now)]
    nm_open_prs = [
        i
        for i in gh_issues
        if i.type == "pr" and i.is_open(now) and not _is_maintainer(i, maintainers)
    ]

    def _closed_count(issues: list, issue_type: str | None) -> int:
        return sum(
            1
            for i in issues
            if (issue_type is None or getattr(i, "type", "issue") == issue_type)
            and i.date_closed is not None
            and i.date_closed >= one_year_ago
        )

    def _nm_closed_count(issues: list, issue_type: str | None) -> int:
        return sum(
            1
            for i in issues
            if (issue_type is None or getattr(i, "type", "issue") == issue_type)
            and i.date_closed is not None
            and i.date_closed >= one_year_ago
            and not _is_maintainer(i, maintainers)
        )

    return SnapshotMetrics(
        open_issues=len(open_issues),
        open_prs=len(open_prs),
        median_issue_age=get_median_age([i.date_opened for i in open_issues], now),
        median_pr_age=get_median_age([i.date_opened for i in open_prs], now),
        closed_issues_year=_closed_count(gh_issues, "issue")
        + _closed_count(lp_bugs, None),
        closed_prs_year=_closed_count(gh_issues, "pr"),
        nm_open_issues=len(nm_open_issues),
        nm_open_prs=len(nm_open_prs),
        nm_median_issue_age=get_median_age(
            [i.date_opened for i in nm_open_issues], now
        ),
        nm_median_pr_age=get_median_age([i.date_opened for i in nm_open_prs], now),
        nm_closed_issues_year=_nm_closed_count(gh_issues, "issue")
        + _closed_count(lp_bugs, None),
        nm_closed_prs_year=_nm_closed_count(gh_issues, "pr"),
    )


def _generate_issue_csv(
    issues: list,
    csv_path: pathlib.Path,
    label: str,
    maintainers: set[str],
) -> None:
    """Write daily open/closed/age data for a flat list of issues to a CSV file.

    Iterates from :data:`CSV_START_DATE` to today. Each row records the number of
    open issues, how many closed that day, and the median age of open issues — both
    overall (``issues``, ``closed``, ``age``) and for the non-maintainer subset
    (``nm_*`` columns).

    :param issues: Flat list of issue/bug objects that implement ``is_open(date)``
        and ``date_closed``.
    :param csv_path: Destination CSV file path.
    :param label: Human-readable name for progress messages.
    :param maintainers: Set of maintainer GitHub usernames. Objects without an
        ``opened_by`` attribute (e.g. Launchpad bugs) are always treated as
        non-maintainer.
    """
    start_date = CSV_START_DATE
    end_date = datetime.now(tz=UTC)
    intermediate_data = IntermediateData()
    emit.progress(f"Counting open issues and age for {label}", permanent=True)

    for date in [
        start_date + timedelta(days=i) for i in range((end_date - start_date).days)
    ]:
        open_issues = [issue for issue in issues if issue.is_open(date)]
        closed_today = sum(
            1
            for issue in issues
            if issue.date_closed is not None and issue.date_closed.date() == date.date()
        )
        nm_open = [i for i in open_issues if not _is_maintainer(i, maintainers)]
        nm_closed = sum(
            1
            for issue in issues
            if issue.date_closed is not None
            and issue.date_closed.date() == date.date()
            and not _is_maintainer(issue, maintainers)
        )
        intermediate_data.data.append(
            IntermediateDataPoint(
                date=date.strftime("%Y-%b-%d"),
                open_issues=len(open_issues),
                closed_issues=closed_today,
                median_age=get_median_age(
                    [issue.date_opened for issue in open_issues], date
                ),
                nm_open_issues=len(nm_open),
                nm_closed_issues=nm_closed,
                nm_median_age=get_median_age(
                    [issue.date_opened for issue in nm_open], date
                ),
            ),
        )

    emit.debug(f"Writing data to {csv_path}")
    IssueDataPoint.save_to_csv(intermediate_data.to_csv_models(), csv_path)
    emit.progress(f"Wrote to {csv_path}", permanent=True)


def _is_maintainer(
    issue: GithubIssue | LaunchpadBug,
    maintainers: set[str],
) -> bool:
    """Return True if the issue was opened by a maintainer.

    Launchpad bugs always return False. GitHub issues return True only when
    ``opened_by`` is set and is in the maintainers set.
    """
    opened_by = getattr(issue, "opened_by", None)
    return opened_by is not None and opened_by in maintainers


def get_median_age(dates: list[datetime] | None, date: datetime) -> int | None:
    """Get the median age in days of a list of dates from a reference date."""
    if dates:
        median_date = get_median_date(dates)
        return (date - median_date).days

    return None


def get_mean_date(dates: list[datetime]) -> datetime:
    """Get mean date from a list of datetimes."""
    reference = datetime(year=2000, month=1, day=1, tzinfo=UTC)
    return reference + sum((date - reference for date in dates), timedelta()) / len(
        dates,
    )


def get_median_date(dates: list[datetime]) -> datetime:
    """Get median date from a list of datetimes."""
    if len(dates) == 0:
        raise ValueError("Cannot get median date from an empty list")

    sorted_dates = sorted(dates)
    n = len(sorted_dates)

    # if the list is even, average the two middle values
    if n % 2 == 0:
        return get_mean_date(sorted_dates[n // 2 - 1 : n // 2 + 1])

    # if the list is odd, return the middle value
    return sorted_dates[n // 2]
