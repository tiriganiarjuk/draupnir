"""Graph build primitives — ref string detection building blocks.

CC=1. Cache keys use the format "level/name" (e.g., "atom/boolean",
"section/task"). These primitives decompose that format for ref
detection and JSON Schema $defs key generation.
"""

from draupnir.structure.config.levels import Level


def ref_prefix(value: str) -> str:
    """Isolate the level segment before the slash via str.partition.

    Uses partition rather than split to avoid allocating a full list
    when only the first segment matters.
    """
    return value.partition("/")[0]


def is_known_level(prefix: str) -> bool:
    """Match against the Level enum to distinguish cache refs from plain strings.

    Generated input models contain both cache key strings (refs) and
    literal strings (titles, descriptions). Only strings whose prefix
    matches a Level member are cache refs.
    """
    return prefix in Level.__members__


def cache_key_to_defs_key(cache_key: str) -> str:
    """Replace the slash with double underscore for JSON Schema $defs compatibility.

    JSON Schema $defs keys cannot contain slashes. The double underscore
    is reversible and preserves readability in the output schema.
    """
    return cache_key.replace("/", "__")
