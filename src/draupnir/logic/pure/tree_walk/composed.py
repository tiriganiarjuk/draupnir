"""Tree analysis for $defs detection and output preparation.

CC=4+ functions. Walks the Verdandi model tree to build reverse
indexes, count shared references, and prepare output structures.

No IO. Pure computation on frozen models.
"""

from collections.abc import Iterator

from pydantic import BaseModel

from draupnir.logic.pure.tree_walk.simple import models_from_dict, models_from_tuple


def iter_child_models(model: BaseModel) -> Iterator[BaseModel]:
    """Yield all direct BaseModel children from a model's fields."""
    for _, value in model:
        if isinstance(value, BaseModel):
            yield value
        elif isinstance(value, dict):
            yield from models_from_dict(value)
        elif isinstance(value, tuple):
            yield from models_from_tuple(value)


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
