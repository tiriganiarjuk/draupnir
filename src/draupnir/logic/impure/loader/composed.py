"""Supply-driven loader — composed-level validation and iteration.

CC=4+ functions. Validates root directory structure and iterates
level directories to collect loading errors.
"""

from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

from draupnir.structure.config.levels import Level


def validate_root(root: Path) -> list[Level]:
    """Validate root directory and return existing level directories."""
    if not root.is_dir():
        error_message = f"verdandi root does not exist: {root}"
        raise ValueError(error_message)
    level_dirs = [level for level in Level if (root / level.name).is_dir()]
    if not level_dirs:
        error_message = (
            f"no level directories found in {root}\n"
            f"  expected directories like pattern/, atom/, field/, etc."
        )
        raise ValueError(error_message)
    return level_dirs


def collect_load_errors(
    level_dirs: list[Level],
    root: Path,
    cache: dict[str, BaseModel],
    try_load_fn: Callable[[str, Path, dict[str, BaseModel]], str | None],
) -> list[str]:
    """Load all files across levels, collecting errors."""
    errors: list[str] = []
    for level in level_dirs:
        level_dir = root / level.name
        for file_path in sorted(level_dir.glob("*.yaml")):
            cache_key = f"{level.name}/{file_path.stem}"
            if cache_key not in cache:
                error = try_load_fn(cache_key, root, cache)
                if error:
                    errors.append(error)
    return errors
