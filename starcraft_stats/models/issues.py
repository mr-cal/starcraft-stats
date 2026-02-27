"""Models for GitHub issues CSV data."""

from typing import ClassVar

from .base import CsvModel


class IssueDataPoint(CsvModel):
    """Data point for GitHub issues CSV output."""

    CSV_HEADERS: ClassVar[list[str]] = ["date", "issues", "issues_avg", "age"]

    date: str
    """The date of this data point."""

    issues: int
    """Number of open issues on this date."""

    issues_avg: int | None = None
    """Rolling average of open issues."""

    age: int | None = None
    """Median age of open issues in days."""

    def to_csv_row(self) -> list[str]:
        """Convert to CSV row format."""
        return [
            self.date,
            str(self.issues),
            str(self.issues_avg) if self.issues_avg is not None else "",
            str(self.age) if self.age is not None else "",
        ]
