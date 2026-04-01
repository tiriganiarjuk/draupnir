"""Graph build primitives — ref string detection building blocks.

CC=1. Single-expression helpers for cache ref string identification.
"""

from draupnir.structure.config.levels import Level


def ref_prefix(value: str) -> str:
    """Extract the part before the first slash. Returns full string if no slash."""
    return value.partition("/")[0]


def is_known_level(prefix: str) -> bool:
    """Check if a string is a known level name."""
    return prefix in Level.__members__


def cache_key_to_defs_key(cache_key: str) -> str:
    """Convert cache key to $defs key.

    'simplegroup/context_item_raw' -> 'simplegroup__context_item_raw'
    """
    return cache_key.replace("/", "__")
