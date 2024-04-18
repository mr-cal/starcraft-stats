"""Get tag and release data for a git repositories."""

import argparse
import git
#import contextlib
import tempfile
import pathlib
#from typing import Iterator

from .config import Config


#@contextlib.contextmanager
#def temp_dir() -> Iterator[pathlib.Path]:
#    with tempfile.TemporaryDirectory() as dir_:
#        yield dir_


def get_releases(
    parsed_args: argparse.Namespace,  # noqa: ARG001 (unused argument)
    config: Config,
) -> None:
    """Get tag and release data for a git repositories."""
    apps = config.craft_applications

    # clone a git repo in a temporary directory
    for app in apps:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = pathlib.Path(temp_dir)
            url = f"https://github.com/{app.owner}/{app.name}.git"

            print(f"Cloning {app} to {temp_dir}")
            git.Repo.clone_from(url, temp_dir)
