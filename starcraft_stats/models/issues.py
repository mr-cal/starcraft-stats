"""Models for GitHub issues CSV data."""

from typing import Annotated, ClassVar

from pydantic import BeforeValidator

from .base import CsvModel


def _empty_str_to_none(v: object) -> object:
    """Convert empty string to None for optional int fields in CSV loading."""
    if v == "":
        return None
    return v


NullableInt = Annotated[int | None, BeforeValidator(_empty_str_to_none)]


class IssueDataPoint(CsvModel):
    """Data point for GitHub issues CSV output."""

    CSV_HEADERS: ClassVar[list[str]] = [
        "date",
        "issues",
        "closed",
        "age",
        "nm_issues",
        "nm_closed",
        "nm_age",
    ]

    date: str
    """The date of this data point."""

    issues: int
    """Number of open issues on this date."""

    closed: int = 0
    """Number of issues closed on this date."""

    age: NullableInt = None
    """Median age of open issues in days."""

    nm_issues: int = 0
    """Number of open non-maintainer issues on this date."""

    nm_closed: int = 0
    """Number of non-maintainer issues closed on this date."""

    nm_age: NullableInt = None
    """Median age of open non-maintainer issues in days."""

    def to_csv_row(self) -> list[str]:
        """Convert to CSV row format."""
        return [
            self.date,
            str(self.issues),
            str(self.closed),
            str(self.age) if self.age is not None else "",
            str(self.nm_issues),
            str(self.nm_closed),
            str(self.nm_age) if self.nm_age is not None else "",
        ]
