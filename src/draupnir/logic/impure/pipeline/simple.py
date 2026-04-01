"""Pipeline helpers — branching functions.

CC=2-3 helpers with iteration or branching.
"""

from pathlib import Path

from draupnir.structure.config.pipeline import PipelineArgs, PipelineContext


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

    Draupnir and verdandi are sibling projects under a common root.
    Walks up from start looking for an ancestor that contains verdandi/.
    Returns None if not found.
    """
    for parent in start.parents:
        if (parent / "verdandi").is_dir():
            return parent
    return None
