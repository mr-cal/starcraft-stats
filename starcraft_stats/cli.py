"""cli handler for starcraft-stats."""

import sys

from craft_cli import (
    ArgumentParsingError,
    CommandGroup,
    CraftError,
    Dispatcher,
    EmitterMode,
    ProvideHelpException,
    emit,
)

from .dependencies import GetDependenciesCommand
from .issues import GetIssuesCommand
from .launchpad import GetLaunchpadDataCommand
from .releases import GetReleasesCommand


def main() -> None:
    """Entrypoint and cli handler."""
    appname = "starcraft-stats"
    emit.init(
        mode=EmitterMode.BRIEF,
        appname=appname,
        greeting="Starting starcraft-stats",
        streaming_brief=True,
    )

    command_groups = CommandGroup(
        "Commands",
        [
            GetDependenciesCommand,
            GetIssuesCommand,
            GetLaunchpadDataCommand,
            GetReleasesCommand,
        ],
    )
    summary = "Retrieve and process data for *craft applications"

    try:
        dispatcher = Dispatcher(
            appname=appname,
            commands_groups=[command_groups],
            summary=summary,
        )
        dispatcher.pre_parse_args(sys.argv[1:])
        dispatcher.load_command(None)
        dispatcher.run()
    except (ArgumentParsingError, ProvideHelpException) as err:
        print(err, file=sys.stderr)  # to stderr, as argparse normally does
        emit.ended_ok()
    except CraftError as err:
        emit.error(err)
    except KeyboardInterrupt as exc:
        error = CraftError("Interrupted.")
        error.__cause__ = exc
        emit.error(error)
    except Exception as exc:  # noqa: BLE001
        error = CraftError(f"Application internal error: {exc!r}")
        error.__cause__ = exc
        emit.error(error)
    else:
        emit.ended_ok()
