"""Schema serialization — single-expression helpers.

CC=1 serialization functions. No branching.
"""


from draupnir.structure.model.schema_output import FragmentDocument, SchemaDocument


def serialize_schema(document: SchemaDocument | FragmentDocument) -> str:
    """Serialize a schema document to formatted JSON string."""
    return document.model_dump_json(by_alias=True, exclude_none=True, indent=2)
