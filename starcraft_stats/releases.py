"""Get tag and release data for a git repositories."""

import argparse
import csv
import pathlib
from dataclasses import dataclass

import git
from craft_cli import BaseCommand, emit

from .application import Application
from .config import CONFIG_FILE, Config

DATA_FILE = pathlib.Path("html/data/releases.csv")


@dataclass(frozen=True)
class BranchInfo:
    """Info about a branch."""

    application: str
    """The name of the application."""

    branch: str
    """The name of the branch."""

    latest_tag: str
    """The latest tag on the branch."""

    commits_since_tag: int
    """The number of commits since the latest tag."""


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

        apps = [
            Application(name=app, full_clone=True) for app in config.craft_applications
        ]

        for app in apps:
            for branch_name, repo_dir in app.local_repos.items():
                repo = git.Repo(path=repo_dir)
                try:
                    tag = repo.git.describe(
                        "--abbrev=0",
                        "--tags",
                        "--match",
                        "[0-9]*.[0-9]*.[0-9]*",
                    )
                    commits_since_tag = repo.git.rev_list("--count", "HEAD", f"^{tag}")
                except git.GitCommandError as err:
                    if "No names found" in str(err):
                        # No tags found, skip this branch
                        emit.debug(f"No tags found for {branch_name}")
                        tag = "0.0.0"
                        commits_since_tag = repo.git.rev_list("--count", "HEAD")
                    else:
                        raise

                emit.debug(
                    f"application: {app.name}, "
                    f"branch: {branch_name}, "
                    f"latest tag: {tag}, "
                    f"commits since tag: {commits_since_tag}",
                )
                branch_infos.append(
                    BranchInfo(
                        app.name,
                        branch_name,
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
