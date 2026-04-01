"""Schema building — single-expression constructors.

CC=1 builders. No branching, no iteration. Each function maps one
generated input model type to its JSON Schema output model, reading
.root through RootModel wrappers to extract the underlying values.

merge_zone_results exists because container builders collect properties
from two separate zone sets (fields + containers) that must be merged
before passing to SchemaObject construction.
"""

from pydantic import BaseModel

from draupnir.structure.config.build_context import BuildContext
from draupnir.structure.model.schema_output import SchemaArray, SchemaConditional, SchemaField


def merge_zone_results(
    zone_a: tuple[dict[str, BaseModel], list[str], list[SchemaConditional]],
    zone_b: tuple[dict[str, BaseModel], list[str], list[SchemaConditional]],
) -> tuple[dict[str, BaseModel], list[str], list[SchemaConditional]]:
    """Combine two zone-set results into one by concatenating all three components.

    Group and shallowsection builders call collect_zone_set twice (fields, containers)
    and need the results unified before passing to build_container_schema.
    """
    a_props, a_req, a_conds = zone_a
    b_props, b_req, b_conds = zone_b
    return {**a_props, **b_props}, a_req + b_req, a_conds + b_conds


def build_pattern(model: BaseModel, context: BuildContext) -> SchemaField:
    """Pattern -> SchemaField with type=string and regex pattern.

    The model's regex field holds the raw regex string via RootModel[str].
    """
    return SchemaField(
        title=model.title.root,
        type="string",
        pattern=model.regex.root,
        description=model.description.root,
    )


def build_enum(model: BaseModel, context: BuildContext) -> SchemaField:
    """Enum -> SchemaField with type=string and enum values.

    values.root is a list of allowed strings from the Verdandi enum definition.
    """
    return SchemaField(
        title=model.title.root,
        type="string",
        enum=tuple(model.values.root),
        description=model.description.root,
    )


def build_simplearray(model: BaseModel, context: BuildContext) -> SchemaArray:
    """Simplearray -> SchemaArray with items from context.

    Unlike array (simple.py), simplearray has a single direct items ref,
    not a typed container that may hold a oneOf. min_items=1 because
    Verdandi arrays are always non-empty.
    """
    return SchemaArray(
        title=model.title.root,
        items=context.built[model.items.root],
        description=model.description.root,
        min_items=1,
    )
