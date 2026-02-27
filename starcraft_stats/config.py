"""Configuration file manager for starcraft-stats."""

from pathlib import Path

from craft_application.models import CraftBaseModel

# you better run this tool from the project root
CONFIG_FILE = Path("starcraft-config.yaml")


class Config(CraftBaseModel):
    """Pydantic model for starcraft-stats configuration."""

    craft_libraries: list[str]
    """A list of all craft libraries."""

    craft_projects: list[str]
    """A list of all craft projects."""

    craft_applications: list[str]
    """A list of all craft applications."""

    refresh_interval_days: int = 7
    """Number of days before refreshing issue data from GitHub."""

    hotfix_min_versions: dict[str, str] = {}
    """Oldest hotfix branch to include per application, as 'major.minor'."""
