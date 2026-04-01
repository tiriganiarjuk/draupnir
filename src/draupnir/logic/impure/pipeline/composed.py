"""Pipeline path resolution and drift detection.

CC=4-8 functions. Resolves Verdandi source and output directories
from CLI arguments and workspace conventions. Compares compiled
schemas against on-disk files for drift detection.
"""

from pathlib import Path

from draupnir.logic.impure.pipeline.primitive import schema_filename
from draupnir.logic.impure.pipeline.simple import path_or_default
from draupnir.logic.impure.writer.primitive import serialize_schema
from draupnir.structure.model.schema_output import SchemaDocument


def resolve_paths(
    verdandi_dir: Path | None,
    output_dir: Path | None,
    workspace_root: Path | None,
    project: str | None = None,
) -> tuple[Path, Path]:
    """Resolve Verdandi source and output directories.

    With --project: reads verdandi/{project}/source/, writes verdandi/{project}/output/.
    Explicit --verdandi-dir and --output-dir override the project-derived paths.
    When both --verdandi-dir and --output-dir are given, workspace_root is not needed.
    """
    if verdandi_dir and output_dir:
        return verdandi_dir, output_dir
    verdandi_root = workspace_root / "verdandi"
    if project:
        verdandi = path_or_default(verdandi_dir, verdandi_root / project / "source")
        output = path_or_default(output_dir, verdandi_root / project / "output")
    else:
        verdandi = path_or_default(verdandi_dir, verdandi_root)
        output = path_or_default(output_dir, workspace_root / "schemas")
    return verdandi, output


def check_schema_drift(
    schemas: dict[str, SchemaDocument],
    output_dir: Path,
) -> list[str]:
    """Compare compiled schemas against on-disk. Returns list of drift messages."""
    messages: list[str] = []
    for cache_key, document in schemas.items():
        path = output_dir / schema_filename(cache_key)
        if not path.exists():
            messages.append(f"missing: {path}")
            continue
        expected = serialize_schema(document)
        if path.read_text().rstrip() != expected:
            messages.append(f"drifted: {path}")
    return messages
