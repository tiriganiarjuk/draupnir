"""Pipeline drift detection.

CC=4-8 functions.

check_schema_drift: compares freshly compiled documents against what is on
  disk. Used by --check mode to detect that source YAML changed and the
  output was not regenerated, or that a generated file was edited. Each
  on-disk file is read through the JSON reader, validated as a JSON Schema
  document, and compared with the compiled document as JSON values.
"""

from pathlib import PurePath

from draupnir.logic.impure.pipeline.ffi import read_json_text
from draupnir.logic.pure.refusal_format.primitive import refusal_text
from draupnir.logic.pure.serialize.primitive import serialize_schema
from draupnir.structure.config.schema_location import SchemaLocation
from draupnir.structure.model.json_document import JsonDocument
from draupnir.structure.model.schema_output import FragmentDocument, SchemaDocument
from draupnir.structure.model.tool_outcome import ToolRefusal


def check_schema_drift(
    documents: dict[str, SchemaDocument | FragmentDocument],
    output_dir: PurePath,
    schema: SchemaLocation,
) -> list[str]:
    """Compare compiled documents against on-disk files. Returns list of drift messages.

    One message per file that differs: `unreadable` when the reader refuses
    it (absent, not JSON, not a JSON Schema document), `drifted` when it
    holds a different JSON value from the compiled document.
    """
    messages: list[str] = []
    for filename, document in documents.items():
        path = output_dir / filename
        outcome = read_json_text(str(path), schema)
        if isinstance(outcome, ToolRefusal):
            messages.append(f"unreadable: {path}: {refusal_text(outcome)}")
            continue
        compiled = JsonDocument.model_validate_json(serialize_schema(document))
        if JsonDocument.model_validate_json(outcome.data) != compiled:
            messages.append(f"drifted: {path}")
    return messages
