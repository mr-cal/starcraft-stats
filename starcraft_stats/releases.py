"""Get tag and release data for a git repositories."""

import argparse
import csv
import pathlib
import tempfile
from dataclasses import dataclass

import git
from craft_cli import BaseCommand, emit

from .config import CONFIG_FILE, Config

DATA_FILE = pathlib.Path("html/data/releases.csv")


@dataclass(frozen=True)
class BranchInfo:
    """Info about a branch."""

    application: str
    branch: str
    latest_tag: str
    commits_since_tag: int


class GetReleasesCommand(BaseCommand):
    """Get tag and release data for git repositories."""

    name = "get-releases"
    help_msg = "Collect tag and release data for git repositories"
    overview = "Collect tag and release data for git repositories"
    common = True

    def run(
        self,
        parsed_args: argparse.Namespace,  # noqa: ARG002 (Unused method argument)
    ) -> None:
        """Get tag and release data for git repositories.

        :param parsed_args: Parsed arguments from the CLI.
        """
        config = Config.from_yaml_file(CONFIG_FILE)

        branch_infos: list[BranchInfo] = []

        # yes this clones a new repo for each branch but
        # pre-optimization is the cause of much suffering
        for app_branch in config.application_branches:
            with tempfile.TemporaryDirectory() as temp_dir:
                url = f"https://github.com/{app_branch.owner}/{app_branch.name}.git"

                emit.debug(f"Cloning {app_branch.name} to {temp_dir}")
                repo = git.Repo.clone_from(url, temp_dir)
                emit.progress(f"Cloned {app_branch.name} to {temp_dir}", permanent=True)
                repo.git.checkout(app_branch.branch)
                tag = repo.git.describe(
                    "--abbrev=0",
                    "--tags",
                    "--match",
                    "[0-9]*.[0-9]*.[0-9]*",
                )
                commits_since_tag = repo.git.rev_list("--count", "HEAD", f"^{tag}")

                emit.debug(
                    f"branch: {app_branch.branch}, "
                    f"latest tag: {tag}, "
                    f"commits since tag: {commits_since_tag}",
                )
                branch_infos.append(
                    BranchInfo(
                        app_branch.name,
                        app_branch.branch,
                        tag,
                        int(commits_since_tag),
                    ),
                )

        # write data to a csv in a ready-to-display format
        emit.debug(f"Writing data to {DATA_FILE}")
        with DATA_FILE.open("w", encoding="utf-8") as file:
            writer = csv.writer(file, lineterminator="\n")
            writer.writerow(["app", "branch", "latest tag", "commits since tag"])
            for branch_info in branch_infos:
                writer.writerow(
                    [
                        branch_info.application,
                        branch_info.branch,
                        branch_info.latest_tag,
                        branch_info.commits_since_tag,
                    ],
                )
        emit.message(f"Wrote to {DATA_FILE}")
