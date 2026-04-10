"""Models for Launchpad bug data."""

from datetime import datetime

from craft_application.models import CraftBaseModel


class LaunchpadBug(CraftBaseModel):
    """Per-bug lifecycle record for a Launchpad bug task."""

    date_opened: datetime
    """When the bug task was created (task.date_created)."""

    date_closed: datetime | None
    """When the bug task was closed (task.date_closed), or None if still open."""

    refresh_date: datetime
    """When this record was last fetched from Launchpad."""

    def is_open(self, date: datetime) -> bool:
        """Check if this bug was open on a particular date."""
        return self.date_opened < date and (
            self.date_closed is None or self.date_closed > date
        )


class LaunchpadBugs(CraftBaseModel):
    """Collection of Launchpad bugs for one project, keyed by bug ID."""

    bugs: dict[int, LaunchpadBug] = {}


class LaunchpadProjects(CraftBaseModel):
    """Collection of Launchpad projects."""

    projects: dict[str, LaunchpadBugs] = {}
