"""Schema writing — through the JSON writer.

CC=1-3. Every schema leaves as text the writer has validated as a JSON
Schema document before the file exists. A refused write is an error line
for the caller to report.
"""

from pathlib import Path

from draupnir.logic.impure.loader.primitive import json_schema_document_schema
from draupnir.logic.impure.writer.ffi import write_json_text
from draupnir.logic.pure.refusal_format.primitive import refusal_text
from draupnir.logic.pure.serialize.primitive import serialize_schema
from draupnir.structure.model.schema_output import FragmentDocument, SchemaDocument
from draupnir.structure.model.tool_outcome import ToolRefusal, ToolWritten


def write_schema_text(json_text: str, path: Path) -> ToolWritten | ToolRefusal:
    """Write JSON Schema text to a file, validated as a JSON Schema document."""
    return write_json_text(json_text, str(path), json_schema_document_schema())


def write_schemas(
    documents: dict[str, SchemaDocument | FragmentDocument], output_dir: Path,
) -> list[str]:
    """Write each document under its filename. Returns one error line per refused write."""
    errors: list[str] = []
    for filename, document in documents.items():
        outcome = write_schema_text(serialize_schema(document), output_dir / filename)
        if isinstance(outcome, ToolRefusal):
            errors.append(f"WRITE ERROR: {filename}: {refusal_text(outcome)}")
    return errors
