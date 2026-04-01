"""Pipeline helpers — path resolution and workspace discovery.

CC=2-3 helpers. Handle the three ways paths can be specified:
1. Explicit CLI args (--verdandi-dir, --output-dir)
2. Project-relative under workspace (--project)
3. Auto-discovered workspace root (walk up from draupnir's location)

find_workspace_root walks up the directory tree looking for a parent
that contains a verdandi/ subdirectory — this is the convention for
the .ai workspace structure where draupnir and verdandi are siblings.
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


def find_workspace_root(start: Path) -> Path | None:
    """Find the workspace root by walking up from a starting path.

    The .ai workspace convention places draupnir and verdandi as siblings
    under a common root (e.g., ~/.ai/smidja/). Walks up from start
    looking for an ancestor that contains a verdandi/ subdirectory.
    Returns None if not found — caller must then require explicit paths.
    """
    for parent in start.parents:
        if (parent / "verdandi").is_dir():
            return parent
    return None
