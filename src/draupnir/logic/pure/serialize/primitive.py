"""Schema serialization and output naming — pure transforms.

CC=1. Model-to-string and key-to-filename conversions. No I/O.

serialize_schema uses Pydantic's model_dump_json with by_alias=True
(so Python field names like "if_" serialize to "if") and exclude_none=True
(so absent optional fields don't appear as null in output). indent=2
matches the established JSON Schema formatting convention.

schema_filename converts cache keys ("schema/task") to output filenames
("task.schema.json"). The split strips the level prefix; the suffix
matches the Verdandi ecosystem convention.
"""

from draupnir.structure.model.schema_output import FragmentDocument, SchemaDocument


def serialize_schema(document: SchemaDocument | FragmentDocument) -> str:
    """Serialize a schema document to formatted JSON string."""
    return document.model_dump_json(by_alias=True, exclude_none=True, indent=2)


def schema_filename(schema_key: str) -> str:
    """Convert cache key to output filename: 'schema/foo' -> 'foo.schema.json'."""
    return schema_key.split("/", 1)[1] + ".schema.json"
