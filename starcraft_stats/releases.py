"""Get tag and release data for git repositories."""

import argparse
import pathlib

import git
from craft_cli import BaseCommand, emit

from .application import Application
from .config import CONFIG_FILE, Config
from .models import ReleaseBranchInfo

DATA_FILE = pathlib.Path("html/data/releases.csv")


def _get_branch_info(
    app_name: str, branch_name: str, repo: git.Repo
) -> ReleaseBranchInfo:
    """Get the latest tag and commit count for a single branch.

    Falls back to tag "0.0.0" with a total commit count if no semver tag exists.
    """
    try:
        tag = repo.git.describe(
            "--abbrev=0",
            "--tags",
            "--match",
            "[0-9]*.[0-9]*.[0-9]*",
        )
        commits_since_tag = repo.git.rev_list("--count", "HEAD", f"^{tag}")
    except git.GitCommandError as err:
        if "No names found" not in str(err):
            raise
        emit.debug(f"No tags found for {branch_name}")
        tag = "0.0.0"
        commits_since_tag = repo.git.rev_list("--count", "HEAD")

    emit.debug(
        f"application: {app_name}, branch: {branch_name}, "
        f"latest tag: {tag}, commits since tag: {commits_since_tag}"
    )
    return ReleaseBranchInfo(
        app=app_name,
        branch=branch_name,
        latest_tag=tag,
        commits_since_tag=int(commits_since_tag),
    )


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
        apps = [
            Application(name=app, full_clone=True) for app in config.craft_applications
        ]

        branch_infos = [
            _get_branch_info(app.name, branch_name, git.Repo(path=repo_dir))
            for app in apps
            for branch_name, repo_dir in app.local_repos.items()
        ]

        emit.debug(f"Writing data to {DATA_FILE}")
        ReleaseBranchInfo.save_to_csv(branch_infos, DATA_FILE)
        emit.message(f"Wrote to {DATA_FILE}")
