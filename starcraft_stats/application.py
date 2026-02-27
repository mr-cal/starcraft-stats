"""Class for a craft application."""

import pathlib
import re
import tempfile
from dataclasses import dataclass
from typing import Any, cast

import git
from craft_cli import emit


@dataclass(frozen=True)
class CraftApplicationBranch:
    """Dataclass for a branch of a craft application."""

    name: str
    branch: str
    owner: str

    def __str__(self) -> str:
        """Return the application name and branch."""
        return f"{self.name}/{self.branch}"


class Application:
    """Application with management of branches and local repositories."""

    name: str
    """The name of the application."""

    local_repos: dict[str, pathlib.Path]
    """A mapping of branches to local repository paths."""

    library_versions: dict[str, str]
    """A mapping of library names to the installed version."""

    branches: list[CraftApplicationBranch]
    """A list of branches of the application."""

    owner: str
    """The owner of the application in github."""

    def __init__(self, name: str, *, full_clone: bool = False) -> None:
        self.name = name
        self.owner = "canonical"
        self.branches = self._get_branches()
        self.local_repos = self.init_local_repos(full_clone=full_clone)

    def _get_branches(self) -> list[CraftApplicationBranch]:
        """Return a list of branches of interest.

        Branches of interest include:
          - main
          - the latest minor release for any hotfix/* branches
        """
        all_branches: list[CraftApplicationBranch] = [
            CraftApplicationBranch(self.name, "main", self.owner)
        ]
        # fetch branch heads from the remote
        raw_head_data: str = cast(
            str,
            git.cmd.Git().ls_remote(
                "--heads",
                f"https://github.com/{self.owner}/{self.name}",
                "refs/heads/hotfix/*",
            ),
        )
        if raw_head_data:
            # convert head data into a list of branch names
            all_hotfix_branches: list[str] = [
                item.split("\t")[1][11:] for item in raw_head_data.split("\n")
            ]

            # get the latest minor release of each major branch
            # for example, out of hotfix/7.5, hotfix/7.6, hotfix/8.0, and hotfix/8.1,
            # we want to keep hotfix/7.6 and hotfix/8.1
            latest: dict[int, tuple[int, str]] = {}
            """Tuple of (minor, branch-name) for each major version."""

            pattern = re.compile(r"hotfix/(\d+)\.(\d+)")

            for branch in all_hotfix_branches:
                match = pattern.match(branch)
                if match:
                    major, minor = map(int, match.groups())
                    if major not in latest or minor > latest[major][0]:
                        latest[major] = (minor, branch)
                else:
                    emit.message(f"Could not parse branch name {branch}")

            hotfix_branches = [item[1] for item in sorted(latest.values())]

            all_branches.extend(
                [
                    CraftApplicationBranch(self.name, branch, self.owner)
                    for branch in hotfix_branches
                ],
            )

        return all_branches

    def init_local_repos(self, *, full_clone: bool) -> dict[str, pathlib.Path]:
        """Initialize all branches into local repos in temporary directories.

        :param full_clone: If true, do a full clone. Else do a shallow (depth=1) clone.
        """
        kwargs: dict[str, Any] = {"depth": 1} if not full_clone else {}

        local_repos: dict[str, pathlib.Path] = {}
        for branch in self.branches:
            safe_name = branch.branch.replace("/", "-")
            repo_path = pathlib.Path(
                tempfile.mkdtemp(prefix=f"starcraft-stats-{self.name}-{safe_name}-")
            )
            local_repos[branch.branch] = repo_path
            emit.debug(f"Cloning {branch} into {repo_path}")
            git.Repo.clone_from(
                url=f"https://github.com/{self.owner}/{self.name}",
                to_path=repo_path,
                branch=branch.branch,
                **kwargs,
            )

        return local_repos
