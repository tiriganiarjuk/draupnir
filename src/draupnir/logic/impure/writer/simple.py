"""Schema writing — file output.

CC=1 writer. Serializes and writes schema documents to disk.
"""

from pathlib import Path

from draupnir.logic.impure.writer.primitive import serialize_schema
from draupnir.structure.model.schema_output import FragmentDocument, SchemaDocument


def write_schema(document: SchemaDocument | FragmentDocument, path: Path) -> Path:
    """Write a schema document as JSON to a file. Returns the path written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize_schema(document) + "\n")
    return path
