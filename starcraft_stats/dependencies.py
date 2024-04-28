"""Fetch craft library requirements for an application."""

import argparse
import json
import pathlib
import subprocess
from collections import defaultdict
from dataclasses import dataclass

import requests
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
    version: str
    latest: str
    outdated: bool


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

        library_versions: dict[str, dict[str, str]] = {}
        latest: dict[str, str] = {}

        # libraries are already installed via project dependencies
        for library in config.craft_libraries:
            emit.debug(f"Collecting version for {library}")
            versions = _get_pip_versions(library)
            latest[library], library_versions[library] = _latest_series_version(
                versions,
            )
            emit.message(f"Parsed latest versions for {library}")

        # a mapping of application branches to their requirements
        app_reqs: dict[str, dict[str, Dependency]] = {}

        # fetch requirements for each application
        for app in config.application_branches:
            app_reqs[f"{app}"] = _get_reqs_for_project(
                app,
                latest,
                library_versions,
                config.craft_libraries,
            )
            emit.message(f"Parsed requirements for {app}")

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
    app: CraftApplicationBranch,
    latest: dict[str, str],
    library_versions: dict[str, dict[str, str]],
    craft_libraries: list[str],
) -> dict[str, Dependency]:
    """Fetch craft library requirements for an application.

    :returns: A list of library names and their version.
    """
    url = (
        f"https://raw.githubusercontent.com/{app.owner}/{app.name}/"
        f"{app.branch}/requirements.txt"
    )
    emit.debug(f"Fetching requirements for {app.name} from {url}")
    reqs_request = requests.get(url, timeout=30)

    if reqs_request.status_code != 200:  # noqa: PLR2004
        raise RuntimeError(f"Could not fetch requirements.txt from {url}")

    df = parse(reqs_request.text, file_type=filetypes.requirements_txt)
    deps: dict[str, str] = {
        dep.name: dep.specs for dep in df.dependencies  # type: ignore[reportUnknownVariableType,reportUnknownMemberType]
    }

    # normalize the version and convert to string
    for dep, spec in deps.items():
        deps[dep] = str(spec).lstrip("=") if spec else "unknown"

    # filter for craft library deps
    libraries = {lib: deps.get(lib, "not used") for lib in craft_libraries}

    dlist: dict[str, Dependency] = {}
    emit.debug(f"Collected requirements for {app.name}:")
    for library_name, library_version in libraries.items():
        emit.debug(f"  {library_name}: {library_version}")

        if library_version in ("unknown", "not used"):
            continue

        ver = Version(library_version)
        series = f"{ver.major}.{ver.minor}"

        if app.branch == "main":
            latest_ver = latest[library_name]
            outdated = library_version not in (latest_ver, "unknown", "not used")
        else:
            # get latest version from series
            latest_ver = library_versions[library_name].get(series, "")
            if latest_ver:
                outdated = library_version not in (latest_ver, "unknown", "not used")
            else:
                outdated = False

        dlist[library_name] = Dependency(
            series=series,
            version=library_version,
            latest=latest_ver,
            outdated=outdated,
        )

    return dlist


def _latest_series_version(versions: list[str]) -> tuple[str, dict[str, str]]:
    series_versions: dict[str, list[str]] = defaultdict(list)
    for version in versions:
        ver = Version(version)
        series = f"{ver.major}.{ver.minor}"
        series_versions[series].append(version)

    latest_ver = "0.0.0"
    series_map: dict[str, str] = {}
    for k, v in series_versions.items():
        v.sort(key=Version, reverse=True)
        series_map[k] = v[0]
        if Version(v[0]) > Version(latest_ver):
            latest_ver = v[0]

    return latest_ver, series_map


def _get_pip_versions(library: str) -> list[str]:
    proc = subprocess.run(
        ["pip", "install", f"{library}==", "--disable-pip-version-check"],
        check=False,
        capture_output=True,
    )
    output = proc.stderr.decode("utf-8").split("\n")[0]

    # get the latest version in each major.minor seriess
    anchor = "from versions: "
    idx = output.find(anchor)
    if idx < 0:
        return []

    versions = output[idx + len(anchor) : -1]
    if versions == "none":
        return []

    return versions.split(", ")
