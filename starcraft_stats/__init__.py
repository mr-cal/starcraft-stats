"""Starcraft stats."""

from typing import List, Optional, Any

try:
    from ._version import __version__
except ImportError:  # pragma: no cover
    from importlib.metadata import version, PackageNotFoundError

    try:
        __version__ = version("starcraft_stats")
    except PackageNotFoundError:
        __version__ = "dev"


def hello(people: Optional[List[Any]] = None) -> None:
    """Says hello."""
    print("Hello *craft team!")
    if people:
        for person in people:
            print(f"Hello {person}!")


__all__ = [
    "__version__",
]
