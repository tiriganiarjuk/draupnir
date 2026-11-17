"""Source files — sort a project's source listing into Verdandi files and strays.

CC=4-8. Directories are passed over: a level directory is not a file, and its
files are listed beneath it.
"""

from pathlib import PurePosixPath

from draupnir.logic.pure.source_files.simple import is_level_file
from draupnir.structure.config.verdandi_manifest import SweptFiles, VerdandiLayout
from draupnir.structure.gen.tools.directory_listing import DirectoryListing, Entry, Kind


def sort_source_files(listing: DirectoryListing, layout: VerdandiLayout) -> SweptFiles:
    """Every file in the listing, as a Verdandi file or a stray, in listing order."""
    level_files: list[Entry] = []
    strays: list[Entry] = []
    for entry in listing.entries:
        if entry.kind is not Kind.file:
            continue
        if is_level_file(PurePosixPath(entry.path), layout):
            level_files.append(entry)
        else:
            strays.append(entry)
    return SweptFiles(level_files=tuple(level_files), strays=tuple(strays))
