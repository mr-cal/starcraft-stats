"""cli handler for starcraft-stats."""

import argparse
import logging

from .dependencies import collect_dependency_data
from .github import collect_github_data
from .launchpad import collect_launchpad_data


def main() -> None:
    """Entrypoint and cli handler."""
    parser = argparse.ArgumentParser(
        description="Collect and process data for starcraft applications and libraries",
    )
    subparsers = parser.add_subparsers(metavar="commands")

    dependencies_parser = subparsers.add_parser(
        "collect-dependency-data",
        help="Collect library usage for *craft applications",
    )
    dependencies_parser.add_argument(
        "-v",
        "--verbose",
        help="Enable verbose logging",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
    )

    dependencies_parser.set_defaults(func=collect_dependency_data)

    fetch_launchpad = subparsers.add_parser(
        "collect-launchpad-data",
        help="Collect data from launchpad",
    )
    fetch_launchpad.add_argument(
        "-v",
        "--verbose",
        help="Enable verbose logging",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
    )
    fetch_launchpad.set_defaults(func=collect_launchpad_data)

    fetch_github = subparsers.add_parser(
        "collect-github-data",
        help="Collect data on open issues from github",
    )
    fetch_github.add_argument(
        "-v",
        "--verbose",
        help="Enable verbose logging",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
    )
    fetch_github.set_defaults(func=collect_github_data)

    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel, format="%(message)s")
    args.func(args)
