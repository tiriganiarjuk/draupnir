"""Schema building — single-expression constructors.

CC=1 builders. No branching, no iteration.
"""

from collections.abc import Callable

from pydantic import BaseModel

from draupnir.structure.model.fields import Enum as VerdandiEnum
from draupnir.structure.model.schema_output import SchemaArray, SchemaConditional, SchemaField
from draupnir.structure.model.simple_containers import Simplearray


def merge_zone_results(
    zone_a: tuple[dict[str, BaseModel], list[str], list[SchemaConditional]],
    zone_b: tuple[dict[str, BaseModel], list[str], list[SchemaConditional]],
) -> tuple[dict[str, BaseModel], list[str], list[SchemaConditional]]:
    """Merge properties, required keys, and conditionals from two zones."""
    a_props, a_req, a_conds = zone_a
    b_props, b_req, b_conds = zone_b
    return {**a_props, **b_props}, a_req + b_req, a_conds + b_conds


def build_enum(enum_model: VerdandiEnum) -> SchemaField:
    """Enum -> {type: string, enum: [...]}."""
    return SchemaField(
        title=enum_model.title,
        type="string",
        enum=enum_model.values,
        description=enum_model.description,
    )


def build_simplearray(
    simplearray: Simplearray,
    build_fn: Callable[[BaseModel], BaseModel],
) -> SchemaArray:
    """Simplearray -> {type: array, items}."""
    return SchemaArray(
        title=simplearray.title,
        items=build_fn(simplearray.items),
        description=simplearray.description,
        min_items=1,
    )
