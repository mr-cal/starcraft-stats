"""Models for GitHub issues and projects."""

from datetime import datetime

from craft_application.models import CraftBaseModel

from .issues import IssueDataPoint


class GithubIssue(CraftBaseModel):
    """Pydantic model for a github issue."""

    type: str
    """The type of issue, either 'issue' or 'pr'."""

    date_opened: datetime
    """The date the issue was opened."""

    date_closed: datetime | None
    """The date the issue was closed, if applicable."""

    refresh_date: datetime
    """The date this issue was last fetched from GitHub."""

    def __str__(self) -> str:
        """Return the issue as a string."""
        date_closed = f" closed: {self.date_closed}" if self.date_closed else ""
        return f"type: {self.type} opened: {self.date_opened}{date_closed}"

    def is_open(self, date: datetime) -> bool:
        """Check if an issue was open on a particular date."""
        return self.date_opened < date and (
            self.date_closed is None or self.date_closed > date
        )


class GithubIssues(CraftBaseModel):
    """Pydantic model for a collection of github issues."""

    issues: dict[int, GithubIssue] = {}
    """A dictionary of issues, indexed by issue number."""


class Projects(CraftBaseModel):
    """Pydantic model for a collection of github projects."""

    projects: dict[str, GithubIssues] = {}
    """A dictionary of projects, indexed by project name."""


class IntermediateDataPoint(CraftBaseModel):
    """Intermediate datapoint about issues for a github project."""

    date: str
    open_issues: int
    open_issues_avg: int | None = None
    mean_age: int | None


class IntermediateData(CraftBaseModel):
    """Intermediate data about issues for a github project."""

    data: list[IntermediateDataPoint] = []

    def to_csv_models(self) -> list[IssueDataPoint]:
        """Convert intermediate data to CSV models."""
        return [
            IssueDataPoint(
                date=point.date,
                issues=point.open_issues,
                issues_avg=point.open_issues_avg,
                age=point.mean_age,
            )
            for point in self.data
        ]
