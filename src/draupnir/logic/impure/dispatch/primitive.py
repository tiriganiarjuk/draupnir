"""$defs-aware dispatch — single-expression helpers.

CC=1 functions. No branching.
"""


def cache_key_to_defs_key(cache_key: str) -> str:
    """Convert cache key to $defs key.

    'simplegroup/context_item_raw' -> 'simplegroup__context_item_raw'
    """
    return cache_key.replace("/", "__")
