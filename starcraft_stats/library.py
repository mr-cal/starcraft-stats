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
        proc = subprocess.run(command, check=False, capture_output=True, text=True)
        emit.trace(f"pip output: {proc.stderr}")

        versions = self._parse_versions_output(proc.stderr.split("\n"))
        if versions is None:
            emit.debug(f"Could not find versions for library {self.name}.")
            return []
        if not versions:
            emit.debug(f"No versions found for library {self.name}.")
        else:
            emit.debug(f"Found versions: {versions}")
        return versions

    @staticmethod
    def _parse_versions_output(lines: list[str]) -> list[Version] | None:
        """Parse pip install error output to extract available versions.

        :returns: A list of versions, an empty list if the library has no versions,
            or None if the expected output line was not found.
        """
        anchor = "from versions: "
        for line in lines:
            emit.trace(f"parsing output line: {line}")
            idx = line.find(anchor)
            if idx < 0:
                emit.trace("Could not find anchor in line")
                continue
            versions_str = line[idx + len(anchor) : -1]
            if versions_str == "none":
                return []
            return [Version(v) for v in versions_str.split(", ")]
        return None
