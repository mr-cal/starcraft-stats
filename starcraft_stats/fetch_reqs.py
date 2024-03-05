"""Fetch craft library requirements for an application."""

import argparse
import csv
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import requests
from dparse import filetypes, parse  # type: ignore[import-untyped]


@dataclass(frozen=True)
class CraftApplication:
    """Dataclass for a craft application."""

    name: str
    branch: str = "main"
    owner: str = "canonical"

    def __str__(self) -> str:
        """Return the application name and branch."""
        return f"{self.name}/{self.branch}"


CRAFT_APPLICATIONS = [
    CraftApplication("charmcraft"),
    CraftApplication("rockcraft"),
    CraftApplication("snapcraft"),
    CraftApplication("snapcraft", "hotfix/7.5"),
    CraftApplication("snapcraft", "hotfix/8.0"),
    CraftApplication("snapcraft", "feature/craft-application"),
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


def get_reqs(parsed_args: argparse.Namespace) -> None:  # noqa: ARG001 (unused argument)
    """Fetch craft library requirements for all applications."""
    library_versions: Dict[str, str] = {}
    # libraries are already installed via project dependencies
    for library in CRAFT_LIBRARIES:
        output = subprocess.check_output(
            ["pip", "show", library, "--disable-pip-version-check"],
        )
        # get version from output
        version = output.decode("utf-8").split("\n")[1].split(": ")[1]
        library_versions[library] = version

    app_reqs: Dict[CraftApplication, Dict[str, str]] = {}
    for app in CRAFT_APPLICATIONS:
        app_reqs[app] = _get_reqs_for_project(app, library_versions)

    # write to data file
    with Path("html/data/app-deps.csv").open("w", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(["library", "latest version", *CRAFT_APPLICATIONS])
        for library in CRAFT_LIBRARIES:
            writer.writerow(
                [
                    library,
                    library_versions[library],
                    *[app_reqs[app][library] for app in CRAFT_APPLICATIONS],
                ],
            )


def _get_reqs_for_project(
    app: CraftApplication,
    library_versions: Dict[str, str],
) -> Dict[str, str]:
    """Fetch craft library requirements for an application.

    :returns: A list of library names and their version.
    """
    url = f"https://raw.githubusercontent.com/{app.owner}/{app.name}/{app.branch}/requirements.txt"
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

    # only return craft library deps
    craft_libraries = {lib: deps.get(lib, "not used") for lib in CRAFT_LIBRARIES}

    for library_name, library_version in craft_libraries.items():
        if library_version == library_versions[library_name]:
            craft_libraries[library_name] = f"✓ {library_version}"
        elif library_version not in ["unknown", "not used"]:
            craft_libraries[library_name] = f"✗ {library_version}"

    return craft_libraries
