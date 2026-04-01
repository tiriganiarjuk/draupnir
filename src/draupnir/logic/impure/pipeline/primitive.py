"""Pipeline helpers — single-expression functions.

CC=1 helpers. No branching.
"""

from pathlib import Path


def schema_filename(schema_key: str) -> str:
    """Convert cache key to output filename: 'schema/foo' -> 'foo.schema.json'."""
    return schema_key.split("/", 1)[1] + ".schema.json"


