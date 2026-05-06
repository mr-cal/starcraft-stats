"""Configuration file manager for starcraft-stats."""

import tomllib
from pathlib import Path
from typing import Self

from craft_application.models import CraftBaseModel

# you better run this tool from the project root
CONFIG_FILE = Path("starcraft-config.toml")


class Config(CraftBaseModel):
    """Pydantic model for starcraft-stats configuration."""

    craft_libraries: list[str]
    """A list of all craft libraries."""

    craft_projects: list[str]
    """A list of all craft projects, in display order."""

    craft_applications: list[str]
    """A list of all craft applications."""

    refresh_interval_days: int = 7
    """Number of days before refreshing issue data from GitHub."""

    hotfix_min_versions: dict[str, str] = {}
    """Oldest hotfix branch to include per application, as 'major.minor'."""

    launchpad_projects: list[str] = []
    """A list of projects whose issues are tracked on Launchpad."""

    maintainers: list[str] = []
    """GitHub usernames of project maintainers."""

    @classmethod
    def from_toml_file(cls, path: Path) -> Self:
        """Instantiate this model from a TOML file."""
        with path.open("rb") as f:
            data = tomllib.load(f)
        return cls.unmarshal(data)
