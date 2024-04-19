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


class CraftApplication(CraftBaseModel):
    """Pydantic model for a craft application."""

    name: str
    """Name of the application."""

    branches: list[str]
    """A list of all branches of interest."""

    owner: str = "canonical"
    """Owner of the application in github."""


class Config(CraftBaseModel):
    """Pydantic model for starcraft-stats configuration."""

    craft_libraries: list[str]
    """A list of all craft libraries."""

    craft_projects: list[str]
    """A list of all craft projects."""

    craft_applications: list[CraftApplication]
    """A list of all craft applications and their branches."""

    @property
    def application_branches(self) -> list[CraftApplicationBranch]:
        """Return a list of all application branches."""
        all_branches: list[CraftApplicationBranch] = []

        for app in self.craft_applications:
            all_branches.extend(
                [
                    CraftApplicationBranch(app.name, branch, app.owner)
                    for branch in app.branches
                ],
            )

        return all_branches
