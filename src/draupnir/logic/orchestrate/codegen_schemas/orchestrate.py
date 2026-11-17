"""Export the manifest schema from the VerdandiManifest model.

The level input schemas under schemas/input/ are the authored source and are
not exported; this writes only schemas/config/verdandi-manifest.schema.json,
through the JSON writer, which validates it as a JSON Schema document.

Entry point: draupnir-export-schemas → cli.py → run_export()
"""

import sys

from draupnir.logic.impure.paths_locate.primitive import locate_draupnir_paths
from draupnir.logic.impure.writer.ffi import write_json_text
from draupnir.logic.pure.refusal_format.primitive import refusal_text
from draupnir.logic.pure.schema_locate.primitive import (
    json_schema_document_schema,
    schema_file_path,
    verdandi_manifest_schema,
)
from draupnir.logic.transform.schema_export.primitive import manifest_schema_node
from draupnir.structure.model.tool_outcome import ToolRefusal


def run_export() -> int:
    """Export the manifest schema. A refused write returns 1."""
    paths = locate_draupnir_paths()
    path = schema_file_path(verdandi_manifest_schema(paths))
    text = manifest_schema_node().model_dump_json(indent=2, by_alias=True, exclude_unset=True)
    outcome = write_json_text(text, path, json_schema_document_schema(paths))
    if isinstance(outcome, ToolRefusal):
        sys.stderr.write(f"WRITE ERROR: {path}: {refusal_text(outcome)}\n")
        return 1
    sys.stdout.write(f"wrote {path}\n")
    return 0
