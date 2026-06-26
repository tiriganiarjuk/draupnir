"""Schema export simple — per-node predicates and constraint builders.

CC=1-3. Building blocks for schema export transforms. Each function
operates on a single node or a single aspect of the schema.
"""

from draupnir.logic.transform.schema_export.primitive import (
    const_true_node,
    extract_ref_target,
    is_defs_ref,
)
from draupnir.structure.model.json_schema_node import JsonSchemaNode


def is_copy_title(title: str | None, level_names: frozenset[str]) -> bool:
    """Check if a $defs entry's title matches a known Level model class."""
    return title is not None and title in level_names


def is_branch_level_ref(branch: JsonSchemaNode, level_names: frozenset[str]) -> bool:
    """Check if one anyOf branch is a $ref to a known Level model.

    Returns False if the branch has no $ref, or the $ref doesn't point
    into $defs, or the target isn't a known level name.
    """
    if branch.ref is None:
        return False
    if not is_defs_ref(branch.ref):
        return False
    return extract_ref_target(branch.ref) in level_names


def is_union_of_level_refs(
    node: JsonSchemaNode,
    level_names: frozenset[str],
) -> bool:
    """Check if a node is an anyOf union where all branches are Level model $refs."""
    if node.any_of is None:
        return False
    return all(is_branch_level_ref(branch, level_names) for branch in node.any_of)


def one_of_required(field_names: tuple[str, ...]) -> list[JsonSchemaNode]:
    """Build a oneOf list where each branch requires exactly one field."""
    return [JsonSchemaNode(required=[name]) for name in field_names]


def any_of_required(field_names: tuple[str, ...]) -> list[JsonSchemaNode]:
    """Build an anyOf list where each branch requires at least one field."""
    return [JsonSchemaNode(required=[name]) for name in field_names]


def collect_present_fields(
    properties: dict[str, JsonSchemaNode],
    candidate_names: tuple[str, ...],
) -> tuple[str, ...]:
    """Filter candidate field names to those present in properties."""
    return tuple(name for name in candidate_names if name in properties)


def encode_conditional_when(node: JsonSchemaNode) -> JsonSchemaNode:
    """Encode ConditionalWhen: exactly one of equals/in/exists, exists must be true."""
    props = node.properties or {}
    new_props = {**props, "exists": const_true_node()} if "exists" in props else props
    return node.model_copy(update={
        "one_of": one_of_required(("equals", "in", "exists")),
        "properties": new_props,
    })


def encode_exactly_one(
    node: JsonSchemaNode,
    field_names: tuple[str, ...],
) -> JsonSchemaNode:
    """Add oneOf constraint for exactly-one-of fields."""
    return node.model_copy(update={"one_of": one_of_required(field_names)})


def encode_at_least_one(
    node: JsonSchemaNode,
    candidate_fields: tuple[str, ...],
) -> JsonSchemaNode:
    """Add anyOf constraint for at-least-one-of present fields."""
    present = collect_present_fields(node.properties or {}, candidate_fields)
    return node.model_copy(update={"any_of": any_of_required(present)})
