"""Loader composed — load all levels into cache.

CC=4+. Populates the model cache by iterating the Level enum in
dependency order (pattern → atom → element → ... → schema). Order
matters because the graph builder assumes all referenced models exist
in the cache when processing a node. Missing level directories are
silently skipped (not all projects use all levels).

Errors are collected rather than raised immediately — this allows
reporting all validation failures in one pass rather than stopping
at the first broken file.
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

    Cache keys are "level/name" (e.g., "atom/safe-string", "schema/task").
    Sorted glob ensures deterministic ordering within each level. Both
    ValueError (gate validation failure) and ValidationError (Pydantic
    model parse failure) are caught — both indicate malformed input YAML.

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
