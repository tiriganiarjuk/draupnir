"""Tree analysis — iterating helpers.

CC=2-3 functions for index building and child traversal.
"""

from collections.abc import Iterator

from pydantic import BaseModel


def reverse_cache_index(cache: dict[str, BaseModel]) -> dict[int, str]:
    """Build id(model) -> cache_key mapping for $defs lookup."""
    return {id(model): cache_key for cache_key, model in cache.items()}


def shared_keys(counts: dict[str, int]) -> frozenset[str]:
    """Return cache keys appearing 2+ times (candidates for $defs)."""
    return frozenset(cache_key for cache_key, count in counts.items() if count >= 2)


def models_from_dict(value: dict[str, BaseModel]) -> Iterator[BaseModel]:
    """Yield BaseModel values from a dict field."""
    for item in value.values():
        if isinstance(item, BaseModel):
            yield item


def models_from_tuple(value: tuple[BaseModel, ...]) -> Iterator[BaseModel]:
    """Yield BaseModel items from a tuple field."""
    for item in value:
        if isinstance(item, BaseModel):
            yield item
