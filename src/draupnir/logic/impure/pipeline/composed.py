"""Pipeline path resolution.

CC=4-8 functions. Resolves Verdandi source and output directories
from CLI arguments and workspace conventions.
"""

from pathlib import Path


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
        verdandi = verdandi_dir or verdandi_root / project / "source"
        output = output_dir or verdandi_root / project / "output"
    else:
        verdandi = verdandi_dir or verdandi_root
        output = output_dir or workspace_root / "schemas"
    return verdandi, output
