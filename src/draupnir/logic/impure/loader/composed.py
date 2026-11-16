"""Loader composed — load all levels into cache.

CC=4+. Populates the model cache by iterating the Level enum in
dependency order (pattern → atom → element → ... → schema). Order
matters because the graph builder assumes all referenced models exist
in the cache when processing a node. A level directory a project does not
have is passed over (not all projects use all levels).

Errors are collected rather than raised immediately — this allows
reporting all validation failures in one pass rather than stopping
at the first broken file.
"""

from pathlib import Path

from pydantic import BaseModel, ValidationError

from draupnir.logic.impure.loader.primitive import schema_dir_path
from draupnir.logic.impure.loader.simple import load_one
from draupnir.logic.pure.refusal_format.primitive import refusal_text
from draupnir.structure.config.levels import Level
from draupnir.structure.model.tool_outcome import ToolRefusal


def load_all_levels(
    root: Path, cache: dict[str, BaseModel],
) -> list[str]:
    """Populate cache with all Verdandi YAML files, bottom-up by level.

    Cache keys are "level/name" (e.g., "atom/safe-string", "schema/task").
    Sorted glob ensures deterministic ordering within each level. A file
    enters the cache only as a parsed input model: a gate refusal (any
    failure class) and a ValidationError (Pydantic model parse failure)
    each leave it out and add an error. A root that yields no files at all
    is an error too.

    Returns a list of error messages (empty on success). The caller reports them.
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
                loaded = load_one(root, level.name, name, schema_dir)
            except ValidationError as exc:
                errors.append(f"LOAD ERROR: {cache_key}: {exc}")
                continue
            if isinstance(loaded, ToolRefusal):
                errors.append(f"LOAD ERROR: {cache_key}: {refusal_text(loaded)}")
                continue
            cache[cache_key] = loaded
    if not cache and not errors:
        errors.append(f"LOAD ERROR: no Verdandi files found under {root}")
    return errors
