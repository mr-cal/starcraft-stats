"""Models for GitHub issues CSV data."""

from typing import ClassVar

from .base import CsvModel


class IssueDataPoint(CsvModel):
    """Data point for GitHub issues CSV output."""

    CSV_HEADERS: ClassVar[list[str]] = ["date", "issues", "closed", "age"]

    date: str
    """The date of this data point."""

    issues: int
    """Number of open issues on this date."""

    closed: int = 0
    """Number of issues closed on this date."""

    age: int | None = None
    """Median age of open issues in days."""

    def to_csv_row(self) -> list[str]:
        """Convert to CSV row format."""
        return [
            self.date,
            str(self.issues),
            str(self.closed),
            str(self.age) if self.age is not None else "",
        ]
