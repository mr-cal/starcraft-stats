"""Get tag and release data for a git repositories."""

import argparse
import pathlib

import git
from craft_cli import BaseCommand, emit

from .application import Application
from .config import CONFIG_FILE, Config
from .models import ReleaseBranchInfo

DATA_FILE = pathlib.Path("html/data/releases.csv")


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

        branch_infos: list[ReleaseBranchInfo] = []

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
                    ReleaseBranchInfo(
                        app=app.name,
                        branch=branch_name,
                        latest_tag=tag,
                        commits_since_tag=int(commits_since_tag),
                    ),
                )

        # write data to a csv in a ready-to-display format
        emit.debug(f"Writing data to {DATA_FILE}")
        ReleaseBranchInfo.save_to_csv(branch_infos, DATA_FILE)
        emit.message(f"Wrote to {DATA_FILE}")
