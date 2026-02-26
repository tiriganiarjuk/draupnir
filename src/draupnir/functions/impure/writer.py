"""Schema serialization and file writing.

model_dump_json(by_alias=True, exclude_none=True) is called here and
NOWHERE ELSE. This is one of exactly two impure files (loader.py reads,
this file writes).
"""

from pathlib import Path

from draupnir.structures.schema_output import SchemaDocument


def serialize_schema(document: SchemaDocument) -> str:
    """Serialize a SchemaDocument to formatted JSON string."""
    return document.model_dump_json(by_alias=True, exclude_none=True, indent=2)


def write_schema(document: SchemaDocument, path: Path) -> Path:
    """Write a SchemaDocument as JSON to a file. Returns the path written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize_schema(document) + "\n")
    return path
