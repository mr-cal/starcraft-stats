"""Pydantic models for snapshot.json and projects.json."""

from craft_application.models import CraftBaseModel


class SnapshotMetrics(CraftBaseModel):
    """Point-in-time metrics for a single project in snapshot.json."""

    open_issues: int
    open_prs: int
    median_issue_age: int | None
    median_pr_age: int | None
    closed_issues_year: int
    closed_prs_year: int
    nm_open_issues: int
    nm_open_prs: int
    nm_median_issue_age: int | None
    nm_median_pr_age: int | None
    nm_closed_issues_year: int
    nm_closed_prs_year: int


class ProjectsData(CraftBaseModel):
    """Shape of the generated projects.json file consumed by the dashboard JS.

    ``ordered`` is a flat list in display order (applications → libraries → other →
    launchpad with the "(launchpad)" suffix).  JS iterates this directly so the
    ordering logic lives in one place (Python / config file) rather than being
    duplicated across every JS file.
    """

    applications: list[str]
    libraries: list[str]
    other: list[str]
    launchpad: list[str]
    ordered: list[str]
