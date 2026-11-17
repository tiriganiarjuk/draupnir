"""Schema writing — through the JSON writer.

CC=1-3. Every schema leaves as text the writer has validated against the
schema location the caller passes — a JSON Schema document, or a schema of its
own — before the file exists. A refused write is an error line for the caller
to report.
"""

from pathlib import PurePath

from draupnir.logic.impure.writer.ffi import write_json_text
from draupnir.logic.pure.refusal_format.primitive import refusal_text
from draupnir.logic.pure.serialize.primitive import serialize_schema
from draupnir.structure.config.schema_location import SchemaLocation
from draupnir.structure.model.schema_output import FragmentDocument, SchemaDocument
from draupnir.structure.model.tool_outcome import ToolRefusal


def write_schemas(
    documents: dict[str, SchemaDocument | FragmentDocument],
    output_dir: PurePath,
    schema: SchemaLocation,
) -> list[str]:
    """Write each document under its filename. Returns one error line per refused write."""
    errors: list[str] = []
    for filename, document in documents.items():
        outcome = write_json_text(serialize_schema(document), str(output_dir / filename), schema)
        if isinstance(outcome, ToolRefusal):
            errors.append(f"WRITE ERROR: {filename}: {refusal_text(outcome)}")
    return errors
