"""Get tag and release data for a git repositories."""

import argparse
import csv
import logging
import pathlib
import tempfile
from dataclasses import dataclass

import git

from .config import Config

logger = logging.getLogger(__name__)

DATA_FILE = pathlib.Path("html/data/releases.csv")


@dataclass(frozen=True)
class BranchInfo:
    """Info about a branch."""

    application: str
    branch: str
    latest_tag: str
    commits_since_tag: int


def get_releases(
    parsed_args: argparse.Namespace,  # noqa: ARG001 (unused argument)
    config: Config,
) -> None:
    """Get tag and release data for a git repositories."""
    branch_infos: list[BranchInfo] = []

    # yes this clones a new repo for each branch but
    # pre-optimization is the cause of much suffering
    for app_branch in config.application_branches:
        with tempfile.TemporaryDirectory() as temp_dir:
            url = f"https://github.com/{app_branch.owner}/{app_branch.name}.git"

            logger.debug(f"Cloning {app_branch.name} to {temp_dir}")
            repo = git.Repo.clone_from(url, temp_dir)
            logger.info(f"Cloned {app_branch.name} to {temp_dir}")
            repo.git.checkout(app_branch.branch)
            tag = repo.git.describe(
                "--abbrev=0",
                "--tags",
                "--match",
                "[0-9]*.[0-9]*.[0-9]*",
            )
            commits_since_tag = repo.git.rev_list("--count", "HEAD", f"^{tag}")

            logger.debug(
                f"branch: {app_branch.branch}, latest tag: {tag}, commits since tag: {commits_since_tag}",
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
    logger.debug(f"Writing data to {DATA_FILE}")
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
    logger.info(f"Wrote to {DATA_FILE}")
