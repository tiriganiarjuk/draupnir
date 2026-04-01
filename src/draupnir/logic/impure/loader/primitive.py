"""Loader primitives — single-expression file operations.

CC=1 helpers. Each does exactly one thing with no branching.
"""

from pathlib import Path


def level_file_path(root: Path, level_name: str, name: str) -> Path:
    """Build the filesystem path for a Verdandi YAML file."""
    return root / level_name / f"{name}.yaml"


def schema_dir_path() -> str:
    """Return the path to the input schema directory."""
    return str(Path(__file__).resolve().parent.parent.parent.parent.parent.parent / "schemas" / "input")
