"""Source sweep assembled — list a project's source tree and sort what it holds.

CC=1-2. Combines the listing (impure, through the reader) with the sort into
Verdandi files and strays (pure/source_files).
"""

from pathlib import PurePath

from draupnir.logic.impure.source_sweep.simple import list_source
from draupnir.logic.pure.source_files.composed import sort_source_files
from draupnir.structure.config.verdandi_manifest import SweptFiles, VerdandiLayout
from draupnir.structure.model.tool_outcome import ToolRefusal


def sweep_source_files(source_root: PurePath, layout: VerdandiLayout) -> SweptFiles | ToolRefusal:
    """The project's files, sorted into Verdandi files and strays, or the reader's refusal."""
    listing = list_source(str(source_root))
    if isinstance(listing, ToolRefusal):
        return listing
    return sort_source_files(listing, layout)
