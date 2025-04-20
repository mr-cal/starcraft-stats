"""Fetch craft library requirements for an application."""

import argparse
import json
import pathlib
import subprocess
import tempfile
import git
from dataclasses import dataclass

from craft_cli import BaseCommand, emit
from dataclasses_json import dataclass_json
from dparse import filetypes, parse  # type: ignore[import-untyped]
from packaging.version import Version

from .config import CONFIG_FILE, Config, CraftApplicationBranch

DATA_FILE = pathlib.Path("html/data/app-deps.json")


@dataclass_json
@dataclass
class Dependency:
    """Craft application dependency."""

    series: str
    """The minor release of the library (3.1)."""

    version: str
    """The full version of the library (3.1.4)."""

    latest: str
    """The latest patch version of the library (3.1.5)."""

    outdated: bool
    """If the library is the latest patch for the minor release."""


@dataclass_json
@dataclass
class DependencyTable:
    """The table containing application dependencies."""

    libs: list[str]
    latest: dict[str, str]
    apps: dict[str, dict[str, Dependency]]


class Library:
    name: str
    """The name of the library."""

    versions: list[Version]
    """A list of all versions of the library."""

    def __init__(self, name: str) -> None:
        self.name = name

        self.versions = self._get_versions()

    @property
    def latest(self) -> Version:
        """Return the latest version of the library."""
        return max(self.versions)

    def latest_in_series(self, version: Version) -> Version:
        target_minor = (version.major, version.minor)
        candidates = [v for v in self.versions if (v.major, v.minor) == target_minor]
        return max(candidates)

    def is_latest_patch(self, version: Version) -> bool:
        """Check if a version is the latest patch version of a minor release series.

        For the 3.2 series with 3.2.0, 3.2.1, and 3.2.2, 3.2.2 is the latest patch version.
        """
        return version == self.latest_in_series(version)

    def _get_versions(self) -> list[Version]:
        """Get a list of versions for a library.

        :returns: A list of versions for the library.
        """
        # `uvx pip install <library>==1111111 --disable-pip-version-check` will show
        # all available versions for the library
        command = ["uvx", "pip", "install", f"{self.name}==1111111", "--disable-pip-version-check"]
        emit.debug(f"Running {' '.join(command)}")
        proc = subprocess.run(command, check=False, capture_output=True)
        output = proc.stderr.decode("utf-8").split("\n")
        emit.trace(f"pip output: {output}")

        for line in output:
            emit.trace(f"parsing output line: {line}")

            # get the latest version in each major.minor seriess
            anchor = "from versions: "
            idx = line.find(anchor)
            if idx < 0:
                emit.trace(f"Could not find anchor {anchor}")
                continue

            versions = line[idx + len(anchor) : -1]
            if versions == "none":
                emit.debug(f"No versions found for library {self.name}.")
                return []

            versions_list = versions.split(", ")
            emit.debug(f"Found versions: {versions_list}")
            return [Version(v) for v in versions_list]

        emit.debug(f"Could not find versions for library {self.name}.")
        return []

class Application:
    name: str
    """The name of the application."""

    local_repos: dict[str, pathlib.Path]
    """A mapping of branches to local repository paths."""

    library_versions: dict[str, str]
    """A mapping of library names to the installed version."""

    branch_wildcards: list[str]
    """A list of branch wildcards from the config."""

    branches: list[CraftApplicationBranch]
    """A list of branches of the application."""

    owner: str
    """The owner of the application in github."""

    def __init__(
        self, name: str, owner: str, branch_wildcards: list[str]
    ) -> None:
        self.name = name
        self.owner = owner
        self.branch_wildcards = branch_wildcards
        self.branches = self._get_branches()
        self.local_repos = self.init_local_repos()


    def _get_branches(self) -> list[CraftApplicationBranch]:
        """Return a list of branches of interest."""
        all_branches = []
        for pattern in self.branch_wildcards:
            # fetch branch heads from the remote
            raw_head_data: str = git.cmd.Git().ls_remote(  # type: ignore[reportUnknownVariableType, reportUnknownMemberType]
                "--heads",
                f"https://github.com/{self.owner}/{self.name}",
                f"refs/heads/{pattern}",
            )
            if not raw_head_data:
                continue
            # convert head data into a list of branch names
            branches: list[str] = [  # type: ignore[reportUnknownVariableType]
                item.split("\t")[1][11:]
                for item in raw_head_data.split("\n")  # type: ignore[reportUnknownVariableType]
            ]

            all_branches.extend(
                [
                    CraftApplicationBranch(self.name, branch, self.owner)
                    for branch in branches
                ],
            )

        return all_branches

    def init_local_repos(self) -> dict[str, pathlib.Path]:
        local_repos = {}
        for branch in self.branches:
            safe_name = branch.branch.replace("/", "-")
            repo_path = tempfile.mkdtemp(prefix=f"starcraft-stats-{self.name}-{safe_name}-")
            local_repos[branch.branch] = repo_path
            emit.debug(f"Cloning {branch} into {repo_path}")
            git.Repo.clone_from(
                url=f"https://github.com/{self.owner}/{self.name}",
                to_path=repo_path,
                branch=branch.branch,
                depth=1,
            )

        return local_repos


class GetDependenciesCommand(BaseCommand):
    """Get craft library requirements for all applications."""

    name = "get-dependencies"
    help_msg = "Collect library usage for *craft applications"
    overview = "Collect library usage for *craft applications"
    common = True

    def run(
        self,
        parsed_args: argparse.Namespace,  # noqa: ARG002 (Unused method argument)
    ) -> None:
        """Fetch craft library requirements for all applications.

        :param parsed_args: parsed command line arguments
        """
        config = Config.from_yaml_file(CONFIG_FILE)

        libraries = {lib: Library(lib) for lib in config.craft_libraries}
        """A mapping of library names to their data."""

        apps = [
            Application(
                name=app.name,
                owner=app.owner,
                branch_wildcards=app.branch_wildcards,
            ) for app in config.craft_applications
        ]

        app_reqs: dict[str, dict[str, Dependency]] = {}
        """A mapping of apps and branches to their library usage."""

        for app in apps:
            for branch_name, repo in app.local_repos.items():
                name = f"{app.name}/{branch_name}"
                emit.debug(f"Fetching requirements for {name}")
                app_reqs[name] = _get_reqs_for_project2(
                    branch_name, repo, libraries
                )
                emit.message(f"Parsed requirements for {name}")

        latest = {lib.name: str(lib.latest) for lib in libraries.values()}

        table = DependencyTable(
            libs=config.craft_libraries,
            latest=latest,
            apps=app_reqs,
        )

        # write dependency data to a json file
        emit.debug(f"Writing data to {DATA_FILE}")
        pathlib.Path(DATA_FILE).write_text(json.dumps(table.to_dict(), indent=4))  # type: ignore[attr-defined]
        emit.message(f"Wrote to {DATA_FILE}")


def _get_reqs_for_project2(
    branch_name: str, repo: pathlib.Path, libs: dict[str, Library]
) -> dict[str, Dependency]:
    """Fetch craft library requirements for an application with uv."""
    # TODO split this out into a function that also falls back to parsing requirements.txt
    emit.debug(f"Fetching requirements for {branch_name} from {repo}")
    reqs = subprocess.run(
        ["uv", "export", "--no-hashes"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout

    df = parse(reqs, file_type=filetypes.requirements_txt)

    deps: dict[str, str] = {
        dep.name: dep.specs
        for dep in df.dependencies  # type: ignore[reportUnknownVariableType,reportUnknownMemberType]
    }
    # normalize the version and convert to string
    for dep, spec in deps.items():
        deps[dep] = str(spec).lstrip("=") if spec else "unknown"

    # filter for craft library deps
    libraries = {lib: deps.get(lib, "not used") for lib in libs.keys()}

    dlist: dict[str, Dependency] = {}
    emit.debug(f"Collected requirements for {branch_name}:")
    for library_name, library_version in libraries.items():
        if library_version in ("unknown", "not used"):
            continue

        ver = Version(library_version)
        series = f"{ver.major}.{ver.minor}"

        # main should have the latest release
        if branch_name == "main":
            latest_ver = libs[library_name].latest
        # other branches should have the latest patch version for a given minor release series
        else:
            latest_ver = libs[library_name].latest_in_series(ver)

        outdated = library_version not in (str(latest_ver), "unknown", "not used")
        emit.trace(f"  {library_name}: {library_version} (latest: {latest_ver})")

        dlist[library_name] = Dependency(
            series=series,
            version=library_version,
            latest=str(latest_ver),
            outdated=outdated,
        )

    return dlist
