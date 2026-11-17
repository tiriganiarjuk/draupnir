"""Loader composed — load every file a project's manifest names into the cache.

CC=4+. Iterates the Level enum in dependency order (pattern → atom → element →
... → schema) and, within each level, the manifest's entries at that level.
Order matters because the graph builder assumes all referenced models exist
in the cache when processing a node. Which files exist comes from the sweep's
manifest; nothing here looks at the disk except through the reader.

Errors are collected rather than raised immediately — this allows
reporting all validation failures in one pass rather than stopping
at the first broken file.
"""

from pathlib import PurePath

from pydantic import BaseModel, ValidationError

from draupnir.logic.impure.loader.simple import load_one
from draupnir.logic.pure.refusal_format.primitive import refusal_text
from draupnir.structure.config.levels import Level
from draupnir.structure.config.verdandi_manifest import VerdandiLayout, VerdandiManifest
from draupnir.structure.model.tool_outcome import ToolRefusal


def load_all_levels(
    root: PurePath,
    manifest: VerdandiManifest,
    layout: VerdandiLayout,
    cache: dict[str, BaseModel],
    schema_dir: str,
) -> list[str]:
    """Populate cache with every Verdandi file the manifest names, bottom-up by level.

    Cache keys are "level/name" (e.g., "atom/safe-string", "schema/task").
    Within a level, files load in manifest order, which is sorted by path. A
    file enters the cache only as a parsed input model: a gate refusal (any
    failure class) and a ValidationError (Pydantic model parse failure) each
    leave it out and add an error. A manifest with no entries is an error too.

    schema_dir is the directory holding the level input schemas the reader
    validates each file against. Returns a list of error messages (empty on
    success). The caller reports them.
    """
    errors: list[str] = []
    for level in Level:
        for entry in manifest.entries:
            if entry.level != level.name:
                continue
            cache_key = f"{level.name}/{entry.name}"
            try:
                loaded = load_one(root, entry, layout, schema_dir)
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
