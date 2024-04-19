import sys

from starcraft_stats import cli


def test_smoketest(mocker):
    mocker.patch.object(sys, "argv", ["starcraft-stats", "get-releases"])
    cli.main()
