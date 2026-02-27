"""Class for a craft application."""

import pathlib
import re
import tempfile
from dataclasses import dataclass
from typing import Any, cast

import git
from craft_cli import emit

_HOTFIX_PATTERN = re.compile(r"hotfix/(\d+)\.(\d+)")


def _parse_min_version(version_str: str | None) -> tuple[int, int] | None:
    """Parse a 'major.minor' version string into a tuple, or return None."""
    if version_str is None:
        return None
    major, _, minor = version_str.partition(".")
    return int(major), int(minor)


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

    branches: list[CraftApplicationBranch]
    """A list of branches of the application."""

    owner: str
    """The owner of the application in github."""

    def __init__(
        self,
        name: str,
        *,
        full_clone: bool = False,
        min_hotfix_version: tuple[int, int] | None = None,
    ) -> None:
        self.name = name
        self.owner = "canonical"
        self.min_hotfix_version = min_hotfix_version
        self.branches = self._get_branches()
        self.local_repos = self._init_local_repos(full_clone=full_clone)

    def _fetch_hotfix_branch_names(self) -> list[str]:
        """Fetch hotfix branch names from the remote via git ls-remote."""
        raw = cast(
            str,
            git.cmd.Git().ls_remote(
                "--heads",
                f"https://github.com/{self.owner}/{self.name}",
                "refs/heads/hotfix/*",
            ),
        )
        if not raw:
            return []
        return [
            line.split("\t")[1].removeprefix("refs/heads/") for line in raw.split("\n")
        ]

    @staticmethod
    def _latest_per_major(
        branch_names: list[str],
        min_version: tuple[int, int] | None = None,
    ) -> list[str]:
        """Return the latest minor hotfix branch for each major version.

        For example, given hotfix/7.5, hotfix/7.6, hotfix/8.0, hotfix/8.1,
        returns [hotfix/7.6, hotfix/8.1].

        If min_version is given, branches with a lower version are excluded.
        """
        # Map of major → (minor, branch-name), keeping the highest minor seen
        latest: dict[int, tuple[int, str]] = {}
        for branch in branch_names:
            match = _HOTFIX_PATTERN.match(branch)
            if match:
                major, minor = map(int, match.groups())
                if min_version and (major, minor) < min_version:
                    continue
                if major not in latest or minor > latest[major][0]:
                    latest[major] = (minor, branch)
            else:
                emit.message(f"Could not parse branch name {branch}")
        return [name for _, (_, name) in sorted(latest.items())]

    def _get_branches(self) -> list[CraftApplicationBranch]:
        """Return branches of interest: main plus the latest hotfix per major version."""
        hotfix_names = self._latest_per_major(
            self._fetch_hotfix_branch_names(), self.min_hotfix_version
        )
        return [
            CraftApplicationBranch(self.name, branch, self.owner)
            for branch in ["main", *hotfix_names]
        ]

    def _init_local_repos(self, *, full_clone: bool) -> dict[str, pathlib.Path]:
        """Clone all branches into temporary directories.

        :param full_clone: If true, do a full clone. Else do a shallow (depth=1) clone.
        """
        kwargs: dict[str, Any] = {} if full_clone else {"depth": 1}

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
