"""Manifest build primitives — one listed Verdandi file into one manifest entry.

CC=1. The entry's path, relative to the source root, is {level}/{name}{suffix}:
its directory is the level and its stem the name.
"""

from pathlib import PurePosixPath

from draupnir.structure.config.verdandi_manifest import LevelName, ManifestEntry
from draupnir.structure.gen.tools.directory_listing import Entry


def manifest_entry(entry: Entry) -> ManifestEntry:
    """The manifest entry for one listed Verdandi file."""
    path = PurePosixPath(entry.path)
    return ManifestEntry(level=LevelName(path.parts[0]), name=path.stem)
