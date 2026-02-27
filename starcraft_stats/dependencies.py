"""Fetch craft library requirements for an application."""

import argparse
import json
import pathlib
import subprocess
from dataclasses import dataclass
from typing import cast

from craft_cli import BaseCommand, emit
from dataclasses_json import dataclass_json
from dparse import filetypes, parse
from packaging.version import Version

from .application import Application
from .config import CONFIG_FILE, Config
from .library import Library

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

        apps = [Application(name=app) for app in config.craft_applications]

        app_reqs: dict[str, dict[str, Dependency]] = {}
        """A mapping of apps and branches to their library usage."""

        for app in apps:
            for branch_name, repo in app.local_repos.items():
                name = f"{app.name}/{branch_name}"
                emit.debug(f"Fetching requirements for {name}")
                app_reqs[name] = _get_reqs_for_project(branch_name, repo, libraries)
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


def _get_reqs_for_project(
    branch_name: str, repo: pathlib.Path, libs: dict[str, Library]
) -> dict[str, Dependency]:
    """Fetch craft library requirements for an application with uv."""
    reqs = _export_reqs(repo)
    df = parse(reqs, file_type=filetypes.requirements_txt)

    deps: dict[str, str] = {}
    for dep in df.dependencies:
        name = cast(str, dep.name)
        specs = cast(str, dep.specs)
        deps[name] = specs

    # normalize the version and convert to string
    for dep, spec in deps.items():
        deps[dep] = str(spec).lstrip("=") if spec else "unknown"

    # filter for craft library deps
    libraries = {lib: deps.get(lib, "not used") for lib in libs}

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


def _export_reqs(repo: pathlib.Path) -> str:
    """Export requirements for a project with uv."""
    emit.debug(f"Exporting requirements for {repo}")
    try:
        return subprocess.run(
            ["uv", "export", "--no-hashes"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except subprocess.CalledProcessError as err:
        emit.debug(f"Error exporting requirements for {repo.name} using uv: {err}")
        emit.debug("Falling back to requirements.txt")
        return (repo / "requirements.txt").read_text()
