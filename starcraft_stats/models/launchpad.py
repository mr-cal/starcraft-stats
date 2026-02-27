"""Models for Launchpad CSV data."""

from typing import ClassVar

from pydantic import ConfigDict, Field

from .base import CsvModel


class LaunchpadDataPoint(CsvModel):
    """Data point for Launchpad bug statistics."""

    model_config = ConfigDict(populate_by_name=True)

    CSV_HEADERS: ClassVar[list[str]] = [
        "timestamp",
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

    timestamp: str
    """Timestamp when the data was collected."""

    new: int = Field(default=0, validation_alias="New")
    incomplete: int = Field(default=0, validation_alias="Incomplete")
    opinion: int = Field(default=0, validation_alias="Opinion")
    invalid: int = Field(default=0, validation_alias="Invalid")
    wont_fix: int = Field(default=0, validation_alias="Won't Fix")
    expired: int = Field(default=0, validation_alias="Expired")
    confirmed: int = Field(default=0, validation_alias="Confirmed")
    triaged: int = Field(default=0, validation_alias="Triaged")
    in_progress: int = Field(default=0, validation_alias="In Progress")
    fix_committed: int = Field(default=0, validation_alias="Fix Committed")
    fix_released: int = Field(default=0, validation_alias="Fix Released")
    does_not_exist: int = Field(default=0, validation_alias="Does Not Exist")

    def to_csv_row(self) -> list[str]:
        """Convert to CSV row format."""
        return [
            self.timestamp,
            str(self.new),
            str(self.incomplete),
            str(self.opinion),
            str(self.invalid),
            str(self.wont_fix),
            str(self.expired),
            str(self.confirmed),
            str(self.triaged),
            str(self.in_progress),
            str(self.fix_committed),
            str(self.fix_released),
            str(self.does_not_exist),
        ]
