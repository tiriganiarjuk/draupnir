"""Schema writing — file output.

CC=1 writer. Creates parent directories if needed (mkdir -p) and writes
the serialized JSON Schema with a trailing newline for POSIX compliance.
Returns the path written so callers can log or collect output paths.
"""

from pathlib import Path

from draupnir.logic.pure.serialize.primitive import serialize_schema
from draupnir.structure.model.schema_output import FragmentDocument, SchemaDocument


def write_schema(document: SchemaDocument | FragmentDocument, path: Path) -> Path:
    """Write a schema document as JSON to a file. Returns the path written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize_schema(document) + "\n")
    return path
