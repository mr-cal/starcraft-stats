"""Configuration file manager for starcraft-stats."""

from dataclasses import dataclass
from pathlib import Path

import git
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
            for branch_pattern in app.branches:
                # fetch branch heads from the remote
                raw_head_data: str = git.cmd.Git().ls_remote(  # type: ignore[reportUnknownVariableType, reportUnknownMemberType]
                    "--heads",
                    f"https://github.com/{app.owner}/{app.name}",
                    f"refs/heads/{branch_pattern}",
                )
                if not raw_head_data:
                    continue
                # convert head data into a list of branch names
                branches: list[str] = [  # type: ignore[reportUnknownVariableType]
                    item.split("\t")[1][11:] for item in raw_head_data.split("\n")  # type: ignore[reportUnknownVariableType]
                ]

                all_branches.extend(
                    [
                        CraftApplicationBranch(app.name, branch, app.owner)
                        for branch in branches
                    ],
                )

        return all_branches
