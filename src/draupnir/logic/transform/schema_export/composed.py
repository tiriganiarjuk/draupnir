"""Schema export composed — multi-step schema transforms.

CC=4-8. Transforms that walk $defs entries applying multiple predicates
or constraint patterns. Each function takes a JsonSchemaNode schema and
returns a transformed copy.
"""

from draupnir.logic.transform.schema_export.primitive import (
    is_level_name,
    string_type_node,
)
from draupnir.logic.transform.schema_export.simple import (
    encode_at_least_one,
    encode_conditional_when,
    encode_exactly_one,
    is_copy_title,
    is_union_of_level_refs,
)
from draupnir.structure.config.schema_export import SchemaExportConfig
from draupnir.structure.model.json_schema_node import JsonSchemaNode


def collect_direct_string_defs(
    defs: dict[str, JsonSchemaNode],
    exclude: str,
    level_names: frozenset[str],
) -> set[str]:
    """First pass: identify $defs that are Level models by name or title."""
    string_defs: set[str] = set()
    for def_name, def_node in defs.items():
        if def_name == exclude:
            continue
        if is_level_name(def_name, level_names):
            string_defs.add(def_name)
        elif is_copy_title(def_node.title, level_names):
            string_defs.add(def_name)
    return string_defs


def collect_union_string_defs(
    defs: dict[str, JsonSchemaNode],
    known_string_names: frozenset[str],
) -> set[str]:
    """Second pass: identify $defs that are anyOf unions of known Level refs."""
    string_defs: set[str] = set()
    for def_name, def_node in defs.items():
        if def_name not in known_string_names and is_union_of_level_refs(def_node, known_string_names):
            string_defs.add(def_name)
    return string_defs


def replace_string_defs(
    schema: JsonSchemaNode,
    string_defs: set[str],
) -> JsonSchemaNode:
    """Replace identified $defs entries with {"type": "string"} nodes."""
    if schema.defs is None:
        return schema
    new_defs = {
        name: string_type_node() if name in string_defs else node
        for name, node in schema.defs.items()
    }
    return schema.model_copy(update={"defs": new_defs})


def encode_constraints(
    schema: JsonSchemaNode,
    config: SchemaExportConfig,
) -> JsonSchemaNode:
    """Encode model validator constraints as JSON Schema constructs.

    Walks $defs and dispatches each entry to its constraint encoder
    based on model name. Finishes with schema-root constraint.
    """
    if schema.defs is None:
        return schema
    new_defs: dict[str, JsonSchemaNode] = {}
    for def_name, def_node in schema.defs.items():
        if def_name == "ConditionalWhen":
            def_node = encode_conditional_when(def_node)
        elif def_name in config.exactly_one_names:
            def_node = encode_exactly_one(def_node, config.conditional_fields)
        elif def_name in config.at_least_one_names:
            def_node = encode_at_least_one(def_node, config.zone_candidate_fields)
        new_defs[def_name] = def_node
    updated = schema.model_copy(update={"defs": new_defs})
    if schema.ref == "#/$defs/Schema" and "Schema" in new_defs:
        schema_node = encode_exactly_one(new_defs["Schema"], ("sections", "shallowsections"))
        new_defs["Schema"] = schema_node
        updated = updated.model_copy(update={"defs": new_defs})
    return updated
