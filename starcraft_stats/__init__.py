"""Starcraft stats."""

from .cli import main


try:
    from ._version import __version__
except ImportError:  # pragma: no cover
    from importlib.metadata import version, PackageNotFoundError

    try:
        __version__ = version("starcraft_stats")
    except PackageNotFoundError:
        __version__ = "dev"


__all__ = [
    "__version__",
    "main",
]
