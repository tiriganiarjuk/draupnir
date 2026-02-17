"""Serialize SchemaDocument to JSON Schema files.

IMPURE: File system writes. This is the ONE place model_dump() is called.
Every other stage in the pipeline works with typed Pydantic models.
"""

import json
from pathlib import Path

from draupnir.structures import SchemaDocument


def serialize_schema(document: SchemaDocument) -> str:
    """Serialize SchemaDocument to a JSON string.

    Used by --check mode to compare without writing files.
    """
    data = document.model_dump(by_alias=True, exclude_none=True)
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def write_schema(document: SchemaDocument, output_path: Path) -> Path:
    """Write SchemaDocument to a JSON Schema file.

    This is the ONLY place in the entire pipeline where
    model_dump() converts typed models to dicts.
    Returns the written path for confirmation.
    """
    json_text = serialize_schema(document)
    output_path.write_text(json_text)
    return output_path
