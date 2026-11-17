"""Source sweep — list a Verdandi project's source tree into the typed listing.

CC=1-3. One listing per project, through the compiled reader; the result is
the listing model or the reader's refusal.
"""

from draupnir.logic.impure.source_sweep.ffi import read_links_followed
from draupnir.structure.gen.tools.directory_listing import DirectoryListing
from draupnir.structure.model.tool_outcome import ToolRefusal


def list_source(source_root: str) -> DirectoryListing | ToolRefusal:
    """List the project's source tree, links followed, or return the reader's refusal."""
    outcome = read_links_followed(source_root)
    if isinstance(outcome, ToolRefusal):
        return outcome
    return DirectoryListing.model_validate_json(outcome.data)
