"""Supply-driven loader — file-level assembly.

CC=1-2 assemblers. Wire loader primitives with ref resolution
and cache management. resolve_fn injected via DI to avoid
impure->transform zone violation.
"""

from collections.abc import Callable
from functools import partial
from pathlib import Path

import yaml
from pydantic import BaseModel

from draupnir.logic.impure.loader.composed import collect_load_errors, validate_root
from draupnir.logic.impure.loader.primitive import (
    level_file_path,
    level_model,
    parse_cache_key,
)


def load_file(
    path: str,
    root: Path,
    cache: dict[str, BaseModel],
    resolve_fn: Callable,
) -> BaseModel:
    """Load a single Verdandi YAML file into the cache."""
    if path in cache:
        return cache[path]
    level_name, name = parse_cache_key(path)
    file_path = level_file_path(root, level_name, name)
    model = level_model(level_name).model_validate(
        resolve_fn(yaml.safe_load(file_path.read_text()), cache),
    )
    cache[path] = model
    return model


def try_load_file(
    cache_key: str,
    root: Path,
    cache: dict[str, BaseModel],
    resolve_fn: Callable,
) -> str | None:
    """Attempt to load a single file. Returns error message or None on success."""
    try:
        load_file(cache_key, root, cache, resolve_fn)
    except (yaml.YAMLError, ValueError, KeyError) as exc:
        return f"{cache_key}: {exc!s}"
    return None


def load_all_levels(
    root: Path,
    cache: dict[str, BaseModel],
    resolve_fn: Callable,
) -> dict[str, BaseModel]:
    """Load all Verdandi YAML files in dependency order."""
    level_dirs = validate_root(root)
    bound_try = partial(try_load_file, resolve_fn=resolve_fn)
    errors = collect_load_errors(level_dirs, root, cache, bound_try)
    if errors:
        details = "\n  ".join(errors)
        error_message = f"{len(errors)} files failed to load:\n  {details}"
        raise ValueError(error_message)
    return cache
