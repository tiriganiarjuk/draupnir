"""Pipeline orchestration — load, export, write.

Three modes:
  run_all   — load everything, export all schemas, write all files (default)
  run_check — generate in memory, compare to on-disk, detect drift
  run_list  — list available schemas
"""

import sys
from pathlib import Path

from pydantic import BaseModel

from draupnir.functions.impure.loader import load_all_levels
from draupnir.functions.impure.writer import serialize_schema, write_schema
from draupnir.functions.pure.exporter import export_all_schemas


def resolve_paths(
    verdandi_dir: Path | None,
    output_dir: Path | None,
    workspace_root: Path,
) -> tuple[Path, Path]:
    """Resolve Verdandi and output directories from args or defaults."""
    verdandi = verdandi_dir or workspace_root / "tools" / "verdandi"
    output = output_dir or workspace_root / "schemas"
    return verdandi, output


def schema_filename(schema_key: str) -> str:
    """Convert cache key to output filename: 'schema/foo' -> 'foo.schema.json'."""
    return schema_key.split("/", 1)[1] + ".schema.json"


def run_all(
    verdandi_root: Path,
    output_dir: Path,
) -> int:
    """Load everything, export all schemas, write all files."""
    cache: dict[str, BaseModel] = {}
    load_all_levels(verdandi_root, cache)
    schemas = export_all_schemas(cache)
    for key, document in schemas.items():
        out = output_dir / schema_filename(key)
        write_schema(document, out)
        sys.stdout.write(f"wrote {out.name}\n")
    return 0


def run_check(
    verdandi_root: Path,
    output_dir: Path,
) -> int:
    """Check for drift without writing. Exit 1 if any schema drifted."""
    cache: dict[str, BaseModel] = {}
    load_all_levels(verdandi_root, cache)
    schemas = export_all_schemas(cache)
    drift = False
    for key, document in schemas.items():
        out = output_dir / schema_filename(key)
        generated = serialize_schema(document) + "\n"
        if not out.exists() or out.read_text() != generated:
            sys.stderr.write(f"DRIFT   {out.name}\n")
            drift = True
        else:
            sys.stdout.write(f"OK      {out.name}\n")
    return 1 if drift else 0


def run_list(verdandi_root: Path) -> int:
    """List available schemas."""
    cache: dict[str, BaseModel] = {}
    load_all_levels(verdandi_root, cache)
    schemas = export_all_schemas(cache)
    for key in sorted(schemas):
        sys.stdout.write(f"{schema_filename(key)}\n")
    return 0
