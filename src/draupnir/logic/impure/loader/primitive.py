"""Loader primitives — single-expression file operations.

CC=1 helpers. Each does exactly one thing with no branching.
"""

from pathlib import Path

from draupnir.structure.config.levels import Level


def parse_cache_key(path: str) -> tuple[str, str]:
    """Split a cache key into (level_name, name)."""
    return path.split("/", 1)


def extract_cache_name(cache_key: str) -> str:
    """Extract the name part from a cache key like 'schema/foo' -> 'foo'."""
    return cache_key.split("/", 1)[1]


def level_file_path(root: Path, level_name: str, name: str) -> Path:
    """Build the filesystem path for a Verdandi YAML file."""
    return root / level_name / f"{name}.yaml"


def level_model(level_name: str) -> type:
    """Return the Pydantic model class for a level."""
    return Level[level_name].value
