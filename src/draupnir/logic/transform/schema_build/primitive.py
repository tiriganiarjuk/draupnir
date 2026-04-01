"""Schema building — single-expression constructors.

CC=1 builders. No branching, no iteration.
"""

from pydantic import BaseModel

from draupnir.structure.config.build_context import BuildContext
from draupnir.structure.model.schema_output import SchemaArray, SchemaConditional, SchemaField


def merge_zone_results(
    zone_a: tuple[dict[str, BaseModel], list[str], list[SchemaConditional]],
    zone_b: tuple[dict[str, BaseModel], list[str], list[SchemaConditional]],
) -> tuple[dict[str, BaseModel], list[str], list[SchemaConditional]]:
    """Merge properties, required keys, and conditionals from two zones."""
    a_props, a_req, a_conds = zone_a
    b_props, b_req, b_conds = zone_b
    return {**a_props, **b_props}, a_req + b_req, a_conds + b_conds


def build_pattern(model: BaseModel, context: BuildContext) -> SchemaField:
    """Pattern -> {type: string, pattern: regex}."""
    return SchemaField(
        title=model.title.root,
        type="string",
        pattern=model.regex.root,
        description=model.description.root,
    )


def build_enum(model: BaseModel, context: BuildContext) -> SchemaField:
    """Enum -> {type: string, enum: [...]}."""
    return SchemaField(
        title=model.title.root,
        type="string",
        enum=tuple(model.values.root),
        description=model.description.root,
    )


def build_simplearray(model: BaseModel, context: BuildContext) -> SchemaArray:
    """Simplearray -> {type: array, items}."""
    return SchemaArray(
        title=model.title.root,
        items=context.built[model.items.root],
        description=model.description.root,
        min_items=1,
    )
