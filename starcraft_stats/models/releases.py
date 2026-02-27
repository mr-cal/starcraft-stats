"""Models for release/branch CSV data."""

from typing import ClassVar

from pydantic import ConfigDict, Field

from .base import CsvModel


class ReleaseBranchInfo(CsvModel):
    """Info about a branch and its releases."""

    model_config = ConfigDict(populate_by_name=True)

    CSV_HEADERS: ClassVar[list[str]] = [
        "app",
        "branch",
        "latest tag",
        "commits since tag",
    ]

    app: str
    """The name of the application."""

    branch: str
    """The name of the branch."""

    latest_tag: str = Field(validation_alias="latest tag")
    """The latest tag on the branch."""

    commits_since_tag: int = Field(validation_alias="commits since tag")
    """The number of commits since the latest tag."""

    def to_csv_row(self) -> list[str]:
        """Convert to CSV row format."""
        return [
            self.app,
            self.branch,
            self.latest_tag,
            str(self.commits_since_tag),
        ]
