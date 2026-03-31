"""Schema writing and sidecar generation.

CC=2-3 functions. File writing with mkdir, dynamic module loading,
and sidecar generation.
"""

import importlib.util
from collections.abc import Callable
from pathlib import Path

from draupnir.logic.impure.writer.primitive import serialize_schema
from draupnir.structure.model.schema_output import FragmentDocument, SchemaDocument


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
    """Generate HTML sidecar from a written JSON Schema file."""
    script = workspace_root / "tools" / "inspect_schema.py"
    if not script.exists():
        return None
    inspect_fn = load_inspect_schema(workspace_root)
    html_text = inspect_fn(schema_path)
    sidecar_path = schema_path.with_suffix(schema_path.suffix + ".html")
    sidecar_path.write_text(html_text)
    return sidecar_path
