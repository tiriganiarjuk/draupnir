"""Serialize SchemaDocument to JSON Schema files and HTML sidecars.

IMPURE: File system writes. This is the ONE place model_dump() is called.
Every other stage in the pipeline works with typed Pydantic models.
"""

import importlib.util
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


def load_inspect_schema(workspace_root: Path):
    """Import inspect_schema() from tools/inspect_schema.py."""
    script = workspace_root / "tools" / "inspect_schema.py"
    spec = importlib.util.spec_from_file_location(
        "inspect_schema", script,
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.inspect_schema


def write_sidecar(schema_path: Path, workspace_root: Path) -> Path:
    """Generate HTML sidecar from a written JSON Schema file.

    Loads inspect_schema.py from the workspace tools directory
    and calls its inspect_schema() function.
    Returns the written sidecar path.
    """
    inspect_fn = load_inspect_schema(workspace_root)
    html = inspect_fn(schema_path)
    sidecar_path = schema_path.with_suffix(schema_path.suffix + ".html")
    sidecar_path.write_text(html)
    return sidecar_path
