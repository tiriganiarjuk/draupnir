"""Loader composed — load all levels into cache.

CC=4+. Iterates Level enum in dependency order, discovers YAML files
per level directory, loads each via gate + generated input model.
"""

import sys
from pathlib import Path

from pydantic import BaseModel, ValidationError

from draupnir.logic.impure.loader.primitive import schema_dir_path
from draupnir.logic.impure.loader.simple import load_one
from draupnir.structure.config.levels import Level


def load_all_levels(
    root: Path, cache: dict[str, BaseModel],
) -> list[str]:
    """Populate cache with all Verdandi YAML files, bottom-up by level.

    Returns a list of error messages (empty on success).
    """
    schema_dir = schema_dir_path()
    errors: list[str] = []
    for level in Level:
        level_dir = root / level.name
        if not level_dir.is_dir():
            continue
        for yaml_path in sorted(level_dir.glob("*.yaml")):
            name = yaml_path.stem
            cache_key = f"{level.name}/{name}"
            try:
                cache[cache_key] = load_one(root, level.name, name, schema_dir)
            except (ValueError, ValidationError) as exc:
                errors.append(f"{cache_key}: {exc}")
                sys.stderr.write(f"  LOAD ERROR: {cache_key}: {exc}\n")
    return errors
