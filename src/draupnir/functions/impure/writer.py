"""Schema serialization and file writing.

model_dump_json(by_alias=True, exclude_none=True) is called here and
NOWHERE ELSE. This is one of exactly two impure files (loader.py reads,
this file writes).
"""

import importlib.util
import json
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

from draupnir.structures.schema_output import SchemaDocument


def serialize_schema(document: SchemaDocument) -> str:
    """Serialize a SchemaDocument to formatted JSON string."""
    return document.model_dump_json(by_alias=True, exclude_none=True, indent=2)


def write_schema(document: SchemaDocument, path: Path) -> Path:
    """Write a SchemaDocument as JSON to a file. Returns the path written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize_schema(document) + "\n")
    return path


def serialize_fragment(
    built: BaseModel,
    schema_id: str,
    defs: dict[str, BaseModel] | None,
) -> str:
    """Serialize a schema fragment to formatted JSON string.

    Merges $schema/$id metadata with the built model's fields.
    Dict usage is at the serialization boundary — exit boundary.
    """
    data = built.model_dump(by_alias=True, exclude_none=True)
    result = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": schema_id,
        **data,
    }
    if defs:
        result["$defs"] = {
            key: defn.model_dump(by_alias=True, exclude_none=True)
            for key, defn in defs.items()
        }
    return json.dumps(result, indent=2)


def write_fragment(
    built: BaseModel,
    defs: dict[str, BaseModel] | None,
    schema_id: str,
    path: Path,
) -> Path:
    """Write a schema fragment as JSON to a file. Returns the path written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize_fragment(built, schema_id, defs) + "\n")
    return path


def load_inspect_schema(workspace_root: Path) -> Callable[[Path], str]:
    """Import inspect_schema() from tools/inspect_schema.py."""
    script = workspace_root / "tools" / "inspect_schema.py"
    spec = importlib.util.spec_from_file_location("inspect_schema", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.inspect_schema


def write_sidecar(schema_path: Path, workspace_root: Path) -> Path:
    """Generate HTML sidecar from a written JSON Schema file.

    Loads inspect_schema.py from the workspace tools directory
    and calls its inspect_schema() function.
    Returns the written sidecar path.
    """
    inspect_fn = load_inspect_schema(workspace_root)
    html_text = inspect_fn(schema_path)
    sidecar_path = schema_path.with_suffix(schema_path.suffix + ".html")
    sidecar_path.write_text(html_text)
    return sidecar_path
