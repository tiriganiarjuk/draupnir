"""CLI command implementations.

IMPURE: File reads (check mode), stdout/stderr writes, path resolution.
Each function implements one CLI command, returning an exit code.
"""

import sys
from pathlib import Path

from draupnir.functions.impure.writers import (
    serialize_schema,
    write_schema,
    write_sidecar,
)
from draupnir.functions.impure.pipeline import (
    discover_schema_paths,
    generate_all_schemas,
    generate_schema,
)


def resolve_paths(
    standards_dir: Path | None,
    output_dir: Path | None,
    workspace_root: Path,
) -> tuple[Path, Path]:
    """Resolve toolcompose root and output directory."""
    standards = standards_dir or workspace_root / "standards" / "toolcompose"
    output = output_dir or workspace_root / "schemas"
    return standards, output


def cmd_list(standards_dir: Path) -> int:
    """List available schema definitions."""
    for path in discover_schema_paths(standards_dir / "schema"):
        sys.stdout.write(f"{path.stem}\n")
    return 0


def cmd_generate_one(
    name: str,
    standards_dir: Path,
    output_dir: Path,
    workspace_root: Path,
) -> int:
    """Generate a single schema with HTML sidecar."""
    schema_name = name.removesuffix(".yaml")
    schema_path = standards_dir / "schema" / f"{schema_name}.yaml"
    if not schema_path.exists():
        sys.stderr.write(f"draupnir: not found: {schema_path}\n")
        return 1
    doc = generate_schema(schema_path, standards_dir)
    out = output_dir / f"{schema_name}.schema.json"
    write_schema(doc, out)
    write_sidecar(out, workspace_root)
    sys.stdout.write(f"wrote {schema_name}.schema.json\n")
    return 0


def cmd_generate_all(
    standards_dir: Path,
    output_dir: Path,
    workspace_root: Path,
) -> int:
    """Generate all schemas with HTML sidecars."""
    schemas = generate_all_schemas(standards_dir)
    if not schemas:
        sys.stderr.write("draupnir: no schemas found\n")
        return 1
    for name, doc in schemas.items():
        out = output_dir / f"{name}.schema.json"
        write_schema(doc, out)
        write_sidecar(out, workspace_root)
        sys.stdout.write(f"wrote {name}.schema.json\n")
    return 0


def cmd_check(standards_dir: Path, output_dir: Path) -> int:
    """Check for drift between generated and on-disk schemas."""
    schemas = generate_all_schemas(standards_dir)
    drift = False
    for name, doc in schemas.items():
        out = output_dir / f"{name}.schema.json"
        generated = serialize_schema(doc)
        if not out.exists():
            sys.stderr.write(f"MISSING {out}\n")
            drift = True
            continue
        if out.read_text() != generated:
            sys.stderr.write(f"DRIFT   {out}\n")
            drift = True
        else:
            sys.stdout.write(f"OK      {out}\n")
    return 1 if drift else 0
