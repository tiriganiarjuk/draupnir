"""Tree analysis for $defs detection and output preparation.

Walks the Verdandi model tree to build reverse indexes, count shared
references, and prepare output structures. Used by the exporter to
identify which models become $defs entries.

No IO. Pure computation on frozen models.
"""

from collections.abc import Iterator

from pydantic import BaseModel

from draupnir.structures.schema_output import SchemaArray, SchemaObject


def reverse_cache_index(cache: dict[str, BaseModel]) -> dict[int, str]:
    """Build id(model) -> cache_key mapping for $defs lookup."""
    return {id(model): key for key, model in cache.items()}


def iter_child_models(model: BaseModel) -> Iterator[BaseModel]:
    """Yield all direct BaseModel children from a model's fields."""
    for _, value in model:
        if isinstance(value, BaseModel):
            yield value
        elif isinstance(value, dict):
            yield from (item for item in value.values() if isinstance(item, BaseModel))
        elif isinstance(value, tuple):
            yield from (item for item in value if isinstance(item, BaseModel))


def count_refs(
    root: BaseModel,
    reverse: dict[int, str],
) -> dict[str, int]:
    """Count cache key occurrences in model tree for $defs detection.

    Iterative walk. Each unique model is visited once, but its cache
    key is counted every time it appears as a child. Keys with count
    >= 2 are shared nodes — candidates for $defs extraction.
    """
    counts: dict[str, int] = {}
    visited: set[int] = set()
    stack = [root]
    while stack:
        model = stack.pop()
        if id(model) in visited:
            continue
        visited.add(id(model))
        for child in iter_child_models(model):
            cache_key = reverse.get(id(child))
            if cache_key:
                counts[cache_key] = counts.get(cache_key, 0) + 1
            stack.append(child)
    return counts


def shared_keys(counts: dict[str, int]) -> frozenset[str]:
    """Return cache keys appearing 2+ times (candidates for $defs)."""
    return frozenset(key for key, count in counts.items() if count >= 2)


def wrap_array_as_object(array: SchemaArray) -> SchemaObject:
    """Wrap a SchemaArray in a SchemaObject with an 'items' property.

    TOML root is always a table — bare arrays can't be represented.
    Include files use 'items' as the key for their array content.
    """
    return SchemaObject(
        title=array.title,
        description=array.description,
        properties={"items": array},
        required=("items",),
        additional_properties=False,
    )
