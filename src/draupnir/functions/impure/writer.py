"""Schema serialization and file writing.

model_dump_json(by_alias=True, exclude_none=True) is called here and
NOWHERE ELSE. This is one of exactly two impure files (loader.py reads,
this file writes).
"""

import importlib.util
from collections.abc import Callable
from pathlib import Path

from draupnir.structures.schema_output import FragmentDocument, SchemaDocument


def serialize_schema(document: SchemaDocument | FragmentDocument) -> str:
    """Serialize a schema document to formatted JSON string."""
    return document.model_dump_json(by_alias=True, exclude_none=True, indent=2)


def write_schema(document: SchemaDocument | FragmentDocument, path: Path) -> Path:
    """Write a schema document as JSON to a file. Returns the path written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize_schema(document) + "\n")
    return path


def load_inspect_schema(workspace_root: Path) -> Callable[[Path], str]:
    """Import inspect_schema() from tools/inspect_schema.py."""
    script = workspace_root / "tools" / "inspect_schema.py"
    spec = importlib.util.spec_from_file_location("inspect_schema", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.inspect_schema


def write_sidecar(schema_path: Path, workspace_root: Path) -> Path | None:
    """Generate HTML sidecar from a written JSON Schema file.

    Returns the written sidecar path, or None if inspect_schema.py
    is not available (pending removal from pipeline).
    """
    script = workspace_root / "tools" / "inspect_schema.py"
    if not script.exists():
        return None
    inspect_fn = load_inspect_schema(workspace_root)
    html_text = inspect_fn(schema_path)
    sidecar_path = schema_path.with_suffix(schema_path.suffix + ".html")
    sidecar_path.write_text(html_text)
    return sidecar_path
