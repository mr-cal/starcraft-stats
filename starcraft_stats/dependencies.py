"""Fetch craft library requirements for an application."""

import argparse
import csv
import logging
import subprocess
from pathlib import Path

import requests
from dparse import filetypes, parse  # type: ignore[import-untyped]

from .config import Config, CraftApplicationBranch

logger = logging.getLogger(__name__)


DATA_FILE = Path("html/data/app-deps.csv")


def get_dependencies(
    parsed_args: argparse.Namespace,  # noqa: ARG001 (unused argument)
    config: Config,
) -> None:
    """Fetch craft library requirements for all applications.

    Data is stored in a CSV formatted as:

    | library   | library's latest version | application 1 | ... |
    | --------- | -------------------------| ------------- | ... |
    | library 1 | 1.2.3                    | 1.2.3         | ... |
    | ...       | ...                      | ...           | ... |

    """
    library_versions: dict[str, str] = {}
    # libraries are already installed via project dependencies
    for library in config.craft_libraries:
        logger.debug(f"Collecting version for {library}")
        output = subprocess.check_output(
            ["pip", "show", library, "--disable-pip-version-check"],
        )
        # get version from output
        version = output.decode("utf-8").split("\n")[1].split(": ")[1]
        logger.info(f"Parsed version {version} for {library}")
        library_versions[library] = version

    # a mapping of application branches to their requirements
    app_reqs: dict[CraftApplicationBranch, dict[str, str]] = {}

    # fetch requirements for each application
    for app in config.application_branches:
        app_reqs[app] = _get_reqs_for_project(
            app,
            library_versions,
            config.craft_libraries,
        )

    # write data to a csv in a ready-to-display format
    logger.debug(f"Writing data to {DATA_FILE}")
    with DATA_FILE.open("w", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(["library", "latest version", *config.application_branches])
        for library in config.craft_libraries:
            writer.writerow(
                [
                    library,
                    library_versions[library],
                    *[app_reqs[app][library] for app in config.application_branches],
                ],
            )
    logger.info(f"Wrote to {DATA_FILE}")


def _get_reqs_for_project(
    app: CraftApplicationBranch,
    library_versions: dict[str, str],
    craft_libraries: list[str],
) -> dict[str, str]:
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
    deps: dict[str, str] = {
        dep.name: dep.specs for dep in df.dependencies  # type: ignore[reportUnknownVariableType,reportUnknownMemberType]
    }

    # normalize the version and convert to string
    for dep, spec in deps.items():
        deps[dep] = str(spec).lstrip("=") if spec else "unknown"

    # filter for craft library deps
    libraries = {lib: deps.get(lib, "not used") for lib in craft_libraries}

    logger.debug(f"Collected requirements for {app.name}:")
    for library_name, library_version in libraries.items():
        logger.debug(f"  {library_name}: {library_version}")

        # prefix a ✓ or ✗ to the version
        if library_version == library_versions[library_name]:
            libraries[library_name] = f"{library_version}"
        elif library_version not in ["unknown", "not used"]:
            libraries[library_name] = f"!{library_version}"

    return libraries
