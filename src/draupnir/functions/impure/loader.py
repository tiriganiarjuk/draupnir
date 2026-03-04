"""Supply-driven loader for Verdandi YAML composition hierarchy.

Globs each level directory in dependency order, validates each YAML file
through the level's Pydantic model, and populates the cache. Lower
levels load first, guaranteeing refs are in cache when higher levels
validate.

This is one of exactly two impure files (IO here + writer.py).
"""

import sys
from pathlib import Path

import yaml
from pydantic import BaseModel

from draupnir.structures.levels import Level


def load_file(
    path: str,
    root: Path,
    cache: dict[str, BaseModel],
) -> BaseModel:
    """Load a single Verdandi YAML file into the cache.

    The path is "level/name" (e.g. "atom/kebab_string"). The file
    is read from root/level/name.yaml and validated through the
    level's Pydantic model with the cache as context.
    """
    if path in cache:
        return cache[path]

    level_name, name = path.split("/", 1)
    level = Level[level_name]
    file_path = root / level_name / f"{name}.yaml"
    data = yaml.safe_load(file_path.read_text())

    model = level.value.model_validate(
        data,
        context={"cache": cache},
    )

    cache[path] = model
    return model


def try_load_file(
    cache_key: str,
    root: Path,
    cache: dict[str, BaseModel],
) -> str | None:
    """Attempt to load a single file. Returns error message or None on success."""
    try:
        load_file(cache_key, root, cache)
    except (yaml.YAMLError, ValueError, KeyError) as exc:
        return f"{cache_key}: {exc!s}"
    return None


def load_all_levels(
    root: Path,
    cache: dict[str, BaseModel],
) -> dict[str, BaseModel]:
    """Load all Verdandi YAML files in dependency order.

    Iterates Level enum (declaration order = dependency order).
    Lower levels load first, so refs are guaranteed in cache when
    higher levels validate. Skips levels whose directories don't exist.
    Returns the populated cache.
    """
    errors: list[str] = []
    for level in Level:
        level_dir = root / level.name
        if not level_dir.is_dir():
            continue
        for file_path in sorted(level_dir.glob("*.yaml")):
            cache_key = f"{level.name}/{file_path.stem}"
            if cache_key not in cache:
                error = try_load_file(cache_key, root, cache)
                if error:
                    errors.append(error)
    if errors:
        sys.stderr.write(f"warning: {len(errors)} files failed to load\n")
        for error in errors:
            sys.stderr.write(f"  {error}\n")
    return cache
