"""$defs-aware dispatch — branching builders.

CC=2-3 functions. Array builders and $defs-or-inline routing.
"""

from collections.abc import Callable

from pydantic import BaseModel

from draupnir.structure.model.complex_containers import (
    Array,
    ArrayOneOf,
    Superarray,
    SuperarrayOneOf,
)
from draupnir.structure.model.schema_output import SchemaArray, SchemaOneOf


def build_array(
    array: Array,
    build_fn: Callable[[BaseModel], BaseModel],
) -> SchemaArray:
    """Array -> {type: array, items: object_or_oneOf}."""
    if isinstance(array.items, ArrayOneOf):
        item_schemas = tuple(build_fn(member) for member in array.items.one_of)
        items = SchemaOneOf(one_of=item_schemas)
    else:
        items = build_fn(array.items)
    return SchemaArray(
        title=array.title, items=items,
        description=array.description, min_items=1,
    )


def build_superarray(
    superarray: Superarray,
    build_fn: Callable[[BaseModel], BaseModel],
) -> SchemaArray:
    """Superarray -> {type: array, items: object_or_oneOf}."""
    if isinstance(superarray.items, SuperarrayOneOf):
        item_schemas = tuple(
            build_fn(member) for member in superarray.items.one_of
        )
        items = SchemaOneOf(one_of=item_schemas)
    else:
        items = build_fn(superarray.items)
    return SchemaArray(
        title=superarray.title, items=items,
        description=superarray.description, min_items=1,
    )
