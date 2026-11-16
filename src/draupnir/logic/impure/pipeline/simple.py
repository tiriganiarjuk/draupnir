"""Pipeline helpers — path resolution and workspace discovery.

CC=2-3 helpers. Handle the three ways a run's paths are specified:
1. Explicit CLI args (--verdandi-dir with --output-dir)
2. Project-relative under workspace (--project)
3. Every project under the auto-discovered workspace root (no path args)

find_workspace_root walks up the directory tree looking for a parent
that contains a verdandi/ subdirectory — this is the convention for
the ai workspace structure where draupnir and verdandi are siblings.
"""

from pathlib import Path

from draupnir.structure.config.pipeline import PipelineArgs, PipelineContext


def path_or_default(explicit: Path | None, fallback: Path) -> Path:
    """Return explicit path if given, otherwise the fallback."""
    return explicit or fallback


def optional_path(value: str | None) -> Path | None:
    """Convert optional string to optional Path."""
    return Path(value) if value else None


def args_to_paths(
    args: PipelineArgs,
) -> tuple[Path | None, Path | None, Path | None]:
    """Extract optional paths from pipeline args."""
    return optional_path(args.verdandi_dir), optional_path(args.output_dir), optional_path(args.workspace)


def context_to_paths(context: PipelineContext) -> tuple[Path, Path]:
    """Extract and convert paths from a resolved pipeline context."""
    return Path(context.verdandi), Path(context.output)


def resolve_paths(
    verdandi_dir: Path | None,
    output_dir: Path | None,
    workspace_root: Path | None,
    project: str | None,
) -> tuple[Path, Path]:
    """Resolve Verdandi source and output directories.

    Both explicit paths given → use them directly, workspace not needed.
    Otherwise the project derives them: verdandi/{project}/source/ and
    verdandi/{project}/output/ under the workspace root, with an explicit
    --verdandi-dir or --output-dir overriding its own side.
    """
    if verdandi_dir and output_dir:
        return verdandi_dir, output_dir
    project_root = workspace_root / "verdandi" / project
    verdandi = path_or_default(verdandi_dir, project_root / "source")
    output = path_or_default(output_dir, project_root / "output")
    return verdandi, output


def list_projects(verdandi_root: Path) -> list[str]:
    """Name every Verdandi project under the root, sorted.

    A project is a directory whose source/ holds a schema level — something
    to compile. The shared core has a type tier only, so it is not listed.
    """
    return sorted(
        entry.name
        for entry in verdandi_root.iterdir()
        if (entry / "source" / "schema").is_dir()
    )


def find_workspace_root(start: Path) -> Path | None:
    """Find the workspace root by walking up from a starting path.

    The ai workspace convention places draupnir and verdandi as siblings
    under a common root (e.g., ~/ai/smidja/). Walks up from start
    looking for an ancestor that contains a verdandi/ subdirectory.
    Returns None if not found — caller must then require explicit paths.
    """
    for parent in start.parents:
        if (parent / "verdandi").is_dir():
            return parent
    return None
