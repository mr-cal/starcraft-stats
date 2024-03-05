"""cli handler for starcraft-stats."""

import argparse

from .fetch_reqs import get_reqs
from .github import get_github_data
from .launchpad import get_launchpad_data


def main() -> None:
    """Entrypoint and cli handler."""
    parser = argparse.ArgumentParser(
        description="Fetch starcraft data from github and launchpad.",
    )

    subparsers = parser.add_subparsers(help="sub-command help")

    fetch_reqs = subparsers.add_parser(
        "fetch-reqs",
        help="Fetch craft library requirements for an application",
    )
    fetch_reqs.set_defaults(func=get_reqs)

    fetch_launchpad = subparsers.add_parser(
        "launchpad",
        help="fetch data from launchpad",
    )
    fetch_launchpad.set_defaults(func=get_launchpad_data)
    fetch_launchpad.add_argument(
        "project",
        help="github user project is under",
        metavar="user",
        type=str,
    )

    fetch_github = subparsers.add_parser("github", help="github options")
    fetch_github.set_defaults(func=get_github_data)
    fetch_github.add_argument(
        "user",
        help="github user project is under",
        metavar="user",
        type=str,
    )
    fetch_github.add_argument(
        "project",
        help="github project",
        metavar="project",
        type=str,
    )

    args = parser.parse_args()
    args.func(args)
