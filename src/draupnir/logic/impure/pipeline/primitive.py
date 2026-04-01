"""Pipeline helpers — single-expression functions.

CC=1 helpers. No branching.
"""

from draupnir.structure.config.fragments import Fragment


def schema_filename(schema_key: str) -> str:
    """Convert cache key to output filename: 'schema/foo' -> 'foo.schema.json'."""
    return schema_key.split("/", 1)[1] + ".schema.json"


def fragment_output_name(fragment: Fragment) -> str:
    """Fragment output name with hyphens: 'include-success-criteria'."""
    return fragment.name.replace("_", "-")
