"""Configuration file manager for starcraft-stats."""

from dataclasses import dataclass
from pathlib import Path

from craft_application.models import CraftBaseModel

# you better run this tool from the project root
CONFIG_FILE = Path("starcraft-config.yaml")


@dataclass(frozen=True)
class CraftApplicationBranch:
    """Dataclass for a branch of a craft application."""

    name: str
    branch: str
    owner: str

    def __str__(self) -> str:
        """Return the application name and branch."""
        return f"{self.name}/{self.branch}"


class Config(CraftBaseModel):
    """Pydantic model for starcraft-stats configuration."""

    craft_libraries: list[str]
    """A list of all craft libraries."""

    craft_projects: list[str]
    """A list of all craft projects."""

    craft_applications: list[str]
    """A list of all craft applications."""
