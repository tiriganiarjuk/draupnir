"""Schema export primitives — single-expression predicates and constructors.

CC=1. Leaf functions for identifying level refs and building
replacement nodes. No branching, no iteration.
"""

from draupnir.structure.model.json_schema_node import JsonSchemaNode


def is_level_name(def_name: str, level_names: frozenset[str]) -> bool:
    """Check if a $defs entry name matches a known Level model class."""
    return def_name in level_names


def extract_ref_target(ref_path: str) -> str:
    """Extract the definition name from a $ref path like '#/$defs/Pattern'."""
    return ref_path.split("/")[-1]


def is_defs_ref(ref_path: str) -> bool:
    """Check if a $ref path points into $defs."""
    return ref_path.startswith("#/$defs/")


def string_type_node() -> JsonSchemaNode:
    """Build a {"type": "string"} replacement node."""
    return JsonSchemaNode(type="string")


def const_true_node() -> JsonSchemaNode:
    """Build a {"const": true} replacement node."""
    return JsonSchemaNode(const=True)
