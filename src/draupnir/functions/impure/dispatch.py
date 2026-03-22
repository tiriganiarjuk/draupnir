"""$defs-aware dispatch for Verdandi model tree.

build_or_ref tracks shared models for $defs. build_model dispatches
to type-specific converters via build_fn closures. Array converters
live here as they are tightly coupled to the dispatch mechanism.

No IO. Pure model-to-model conversion with $defs tracking.
"""

from collections.abc import Callable

from pydantic import BaseModel

from draupnir.functions.pure.converters.defs import (
    build_simplearray_refs, build_simplegroup_refs, build_tuple_refs,
    build_union_refs,
)
from draupnir.functions.pure.converters.field_meta import (
    build_verdandi_field_refs,
)
from draupnir.functions.pure.converters.field import build_field
from draupnir.functions.pure.converters.top_level import (
    build_group, build_section, build_shallowsection,
)
from draupnir.structures.complex_containers import (
    Array, ArrayOneOf, Group, Superarray, SuperarrayOneOf,
)
from draupnir.structures.fields import Tuple_, Union_
from draupnir.structures.schema_output import SchemaArray, SchemaOneOf, SchemaRef
from draupnir.structures.simple_containers import (
    Simplearray, Simplegroup, VerdandiField,
)
from draupnir.structures.top_level import Section, Shallowsection


def cache_key_to_defs_key(cache_key: str) -> str:
    """Convert cache key to $defs key.

    'simplegroup/context_item_raw' -> 'simplegroup__context_item_raw'
    """
    return cache_key.replace("/", "__")


def build_or_ref(
    model: BaseModel,
    reverse: dict[int, str],
    shared: frozenset[str],
    defs: dict[str, BaseModel],
) -> BaseModel:
    """Build schema for a model, or return $ref if shared."""
    cache_key = reverse.get(id(model))
    if cache_key and cache_key in shared:
        def_name = cache_key_to_defs_key(cache_key)
        if def_name not in defs:
            defs[def_name] = build_model(model, reverse, shared, defs)
        return SchemaRef(ref=f"#/$defs/{def_name}")
    return build_model(model, reverse, shared, defs)


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


def make_build_fn(
    reverse: dict[int, str],
    shared: frozenset[str],
    defs: dict[str, BaseModel],
) -> Callable[[BaseModel], BaseModel]:
    """Create a build_fn closure over $defs context."""
    def build_fn(model: BaseModel) -> BaseModel:
        return build_or_ref(model, reverse, shared, defs)
    return build_fn


def build_model(
    model: BaseModel,
    reverse: dict[int, str],
    shared: frozenset[str],
    defs: dict[str, BaseModel],
) -> BaseModel:
    """Dispatch any Verdandi model to its type-specific converter."""
    build_fn = make_build_fn(reverse, shared, defs)
    if isinstance(model, Simplegroup):
        return build_simplegroup_refs(model, build_fn)
    if isinstance(model, Tuple_):
        return build_tuple_refs(model, build_fn)
    if isinstance(model, Simplearray):
        return build_simplearray_refs(model, build_fn)
    if isinstance(model, Union_):
        return build_union_refs(model, build_fn)
    if isinstance(model, Group):
        return build_group(model, build_fn)
    if isinstance(model, Array):
        return build_array(model, build_fn)
    if isinstance(model, Superarray):
        return build_superarray(model, build_fn)
    if isinstance(model, Section):
        return build_section(model, build_fn)
    if isinstance(model, Shallowsection):
        return build_shallowsection(model, build_fn)
    if isinstance(model, VerdandiField):
        return build_verdandi_field_refs(model, build_fn)
    return build_field(model)
