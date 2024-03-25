"""Fetch craft library requirements for an application."""

import argparse
import csv
import subprocess
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import requests
from dparse import filetypes, parse  # type: ignore[import-untyped]


logger = logging.getLogger(__name__)


DATA_FILE = Path("html/data/app-deps.csv")


@dataclass(frozen=True)
class CraftApplicationBranch:
    """Dataclass for a craft application."""

    name: str
    branch: str
    owner: str = "canonical"

    def __str__(self) -> str:
        """Return the application name and branch."""
        return f"{self.name}/{self.branch}"


CRAFT_APPLICATION_BRANCHES = [
    CraftApplicationBranch("charmcraft", "main"),
    CraftApplicationBranch("rockcraft", "main"),
    CraftApplicationBranch("snapcraft", "main"),
    CraftApplicationBranch("snapcraft", "hotfix/7.5"),
    CraftApplicationBranch("snapcraft", "hotfix/8.0"),
    CraftApplicationBranch("snapcraft", "feature/craft-application"),
]


CRAFT_LIBRARIES = {
    "craft-application",
    "craft-archives",
    "craft-cli",
    "craft-grammar",
    "craft-parts",
    "craft-providers",
    "craft-store",
}


def collect_dependency_data(
    parsed_args: argparse.Namespace  # noqa: ARG001 (unused argument)
) -> None:
    """Fetch craft library requirements for all applications.

    Data is stored in a CSV formatted as:

    | library   | library's latest version | application 1 | ... |
    | --------- | -------------------------| ------------- | ... |
    | library 1 | 1.2.3                    | 1.2.3         | ... |
    | ...       | ...                      | ...           | ... |

    """
    library_versions: Dict[str, str] = {}
    # libraries are already installed via project dependencies
    for library in CRAFT_LIBRARIES:
        logger.debug(f"Collecting version for {library}")
        output = subprocess.check_output(
            ["pip", "show", library, "--disable-pip-version-check"],
        )
        # get version from output
        version = output.decode("utf-8").split("\n")[1].split(": ")[1]
        logger.info(f"Parsed version {version} for {library}")
        library_versions[library] = version

    app_reqs: Dict[CraftApplicationBranch, Dict[str, str]] = {}
    for app in CRAFT_APPLICATION_BRANCHES:
        app_reqs[app] = _get_reqs_for_project(app, library_versions)

    # write data to a csv in a ready-to-display format
    logger.debug(f"Writing data to {DATA_FILE}")
    with Path("html/data/app-deps.csv").open("w", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(["library", "latest version", *CRAFT_APPLICATION_BRANCHES])
        for library in CRAFT_LIBRARIES:
            writer.writerow(
                [
                    library,
                    library_versions[library],
                    *[app_reqs[app][library] for app in CRAFT_APPLICATION_BRANCHES],
                ],
            )
    logger.info(f"Wrote to {DATA_FILE}")


def _get_reqs_for_project(
    app: CraftApplicationBranch,
    library_versions: Dict[str, str],
) -> Dict[str, str]:
    """Fetch craft library requirements for an application.

    :returns: A list of library names and their version.
    """
    url = (
        f"https://raw.githubusercontent.com/{app.owner}/{app.name}/"
        f"{app.branch}/requirements.txt"
    )
    logger.debug(f"Fetching requirements for {app.name} from {url}")
    reqs_request = requests.get(url, timeout=30)

    if reqs_request.status_code != 200:  # noqa: PLR2004
        raise RuntimeError(f"Could not fetch requirements.txt from {url}")

    df = parse(reqs_request.text, file_type=filetypes.requirements_txt)
    deps: Dict[str, str] = {
        dep.name: dep.specs for dep in df.dependencies  # type: ignore[reportUnknownVariableType,reportUnknownMemberType]
    }

    # normalize the version and convert to string
    for dep, spec in deps.items():
        deps[dep] = str(spec).lstrip("=") if spec else "unknown"

    # filter for craft library deps
    craft_libraries = {lib: deps.get(lib, "not used") for lib in CRAFT_LIBRARIES}

    logger.debug(f"Collected requirements for {app.name}:")
    for library_name, library_version in craft_libraries.items():
        logger.debug(f"  {library_name}: {library_version}")

        # prefix a ✓ or ✗ to the version
        if library_version == library_versions[library_name]:
            craft_libraries[library_name] = f"✓ {library_version}"
        elif library_version not in ["unknown", "not used"]:
            craft_libraries[library_name] = f"✗ {library_version}"

    return craft_libraries
