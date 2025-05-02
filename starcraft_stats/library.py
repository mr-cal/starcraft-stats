"""Class for a craft library."""

import subprocess

from craft_cli import emit
from packaging.version import Version


class Library:
    """A python library with all its versions."""

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
        """Given a version, find the latest patch release in the same minor series."""
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
        command = [
            "uvx",
            "pip",
            "install",
            f"{self.name}==1111111",
            "--disable-pip-version-check",
        ]
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
