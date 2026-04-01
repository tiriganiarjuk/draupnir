"""Pipeline path resolution and drift detection.

CC=4-8 functions. Two responsibilities:

resolve_paths: resolves the Verdandi source and output directories from
  the combination of explicit CLI args, --project shorthand, and workspace
  root. Priority: explicit > project-derived > workspace defaults. The
  --project flag maps to verdandi/{project}/source/ and verdandi/{project}/output/
  under the workspace root — this is the convention for multi-project workspaces.

check_schema_drift: compares freshly compiled schemas against what's on disk.
  Used by --check mode to detect when source YAML changed but schemas weren't
  regenerated. Serializes each compiled schema and does string comparison
  against the file content (rstrip to handle trailing newline differences).
"""

from pathlib import Path

from draupnir.logic.impure.pipeline.simple import path_or_default
from draupnir.logic.pure.serialize.primitive import schema_filename, serialize_schema
from draupnir.structure.model.schema_output import SchemaDocument


def resolve_paths(
    verdandi_dir: Path | None,
    output_dir: Path | None,
    workspace_root: Path | None,
    project: str | None = None,
) -> tuple[Path, Path]:
    """Resolve Verdandi source and output directories.

    Resolution priority (highest first):
    1. Both explicit paths given → use directly, workspace not needed
    2. --project given → derive from verdandi/{project}/source/ and /output/
    3. Neither → fall back to verdandi/ root and workspace/schemas/

    Explicit --verdandi-dir and --output-dir override project-derived paths
    individually (you can mix explicit source with project-derived output).
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
    """Compare compiled schemas against on-disk files. Returns list of drift messages.

    Detects two types of drift: missing files (not yet generated) and content
    differences (source YAML changed but output not regenerated). Serializes
    each schema fresh to compare, ensuring the comparison uses the same
    formatting as write_schema would produce.
    """
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
