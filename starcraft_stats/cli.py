"""cli handler for starcraft-stats."""

import argparse
import logging

from .config import CONFIG_FILE, Config
from .dependencies import get_dependencies
from .issues import get_issues
from .launchpad import get_launchpad_data
from .releases import get_releases


def main() -> None:
    """Entrypoint and cli handler."""
    parser = argparse.ArgumentParser(
        description="Collect and process data for starcraft applications and libraries",
    )
    subparsers = parser.add_subparsers(metavar="commands")

    dependencies_command = subparsers.add_parser(
        "get-dependencies",
        help="Collect library usage for *craft applications",
    )
    dependencies_command.add_argument(
        "-v",
        "--verbose",
        help="Enable verbose logging",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
    )

    dependencies_command.set_defaults(func=get_dependencies)

    launchpad_command = subparsers.add_parser(
        "get-launchpad-data",
        help="Collect data from launchpad",
    )
    launchpad_command.add_argument(
        "-v",
        "--verbose",
        help="Enable verbose logging",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
    )
    launchpad_command.set_defaults(func=get_launchpad_data)

    issues_command = subparsers.add_parser(
        "get-issues",
        help="Collect data on open issues from github",
    )
    issues_command.add_argument(
        "-v",
        "--verbose",
        help="Enable verbose logging",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
    )
    issues_command.set_defaults(func=get_issues)

    releases_command = subparsers.add_parser(
        "get-releases",
        help="Collect tag and release data for git repositories",
    )
    releases_command.add_argument(
        "-v",
        "--verbose",
        help="Enable verbose logging",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
    )
    releases_command.set_defaults(func=get_releases)

    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel, format="%(message)s")

    config = Config.from_yaml_file(CONFIG_FILE)

    args.func(args, config)
