"""FFI reader wrapper — list a Verdandi source tree with its links followed.

CC=1. Thin wrapper around the PyO3 read_directory_links_followed_json module
(nornir readers/). A project's type-tier level directories are symlinks into
core; this reader follows them, so core's files are listed under the project's
own level names.
"""

import read_directory_links_followed_json

from draupnir.structure.model.tool_outcome import ToolRefusal, ToolResult, ToolSuccess


def read_links_followed(root: str) -> ToolSuccess | ToolRefusal:
    """List every entry under root, links followed, and type the result.

    A ToolSuccess carries the listing JSON, validated against Nornir's
    directory-listing schema, in `data`. A ToolRefusal carries the failure
    class in `error.type` and the message in `error.message`.
    """
    result = read_directory_links_followed_json.read(root)
    return ToolResult.model_validate(result).root
