"""Basic Starcraft package demo unit tests."""

# pyright: reportFunctionMemberAccess=false
from unittest import mock

import starcraft_stats


def test_version():
    assert starcraft_stats.__version__ is not None


def test_hello(mocker):
    mocker.patch("builtins.print")

    starcraft_stats.hello()

    print.assert_called_once_with("Hello *craft team!")


def test_hello_people(mocker):
    mocker.patch("builtins.print")

    starcraft_stats.hello(["people"])

    print.assert_has_calls(
        [
            mock.call("Hello *craft team!"),
            mock.call("Hello people!"),
        ],
    )
