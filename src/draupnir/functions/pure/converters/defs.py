"""$defs-aware container converters.

Converts Simplegroup, Tuple, Simplearray, Union, VerdandiField into
JSON Schema output models with $ref support. All functions receive
build_fn for recursive descent through the $defs-tracking dispatch.

No IO. Pure model-to-model conversion.
"""

from collections.abc import Callable

from pydantic import BaseModel

from draupnir.functions.pure.converters.extension import (
    concat_field_description,
    convert_constraints,
    convert_semantic,
    extract_type_min_length,
    resolve_field_min_length,
)
from draupnir.functions.pure.converters.zone import (
    collect_conditional,
    collect_required_optional,
)
from draupnir.structures.fields import Union_
from draupnir.structures.schema_output import (
    SchemaArray,
    SchemaConstraintBlock,
    SchemaField,
    SchemaObject,
    SchemaOneOfField,
    SchemaRef,
    SchemaSemanticExt,
    SchemaTupleArray,
)
from draupnir.structures.simple_containers import (
    Simplearray,
    Simplegroup,
    Tuple_,
    VerdandiField,
)


def build_simplegroup_refs(
    simplegroup: Simplegroup,
    build_fn: Callable[[BaseModel], BaseModel],
) -> SchemaObject:
    """Simplegroup -> {type: object} with $defs-aware field building."""
    properties, required_keys = collect_required_optional(
        simplegroup.required, simplegroup.optional, build_fn,
    )
    cond_props, conditionals = collect_conditional(
        simplegroup.conditional, build_fn,
    )
    properties.update(cond_props)
    return SchemaObject(
        title=simplegroup.title,
        properties=properties,
        required=tuple(required_keys) if required_keys else None,
        additional_properties=False,
        all_of=tuple(conditionals) if conditionals else None,
        description=simplegroup.description,
    )


def build_tuple_refs(
    tuple_model: Tuple_,
    build_fn: Callable[[BaseModel], BaseModel],
) -> SchemaTupleArray:
    """Tuple -> {prefixItems, items: false} with $defs-aware item building."""
    prefix = tuple(build_fn(item) for item in tuple_model.items)
    return SchemaTupleArray(
        title=tuple_model.title,
        prefix_items=prefix,
        description=tuple_model.description,
        min_items=len(prefix),
        max_items=len(prefix),
    )


def build_simplearray_refs(
    simplearray: Simplearray,
    build_fn: Callable[[BaseModel], BaseModel],
) -> SchemaArray:
    """Simplearray -> {type: array, items} with $defs-aware item building."""
    return SchemaArray(
        title=simplearray.title,
        items=build_fn(simplearray.items),
        description=simplearray.description,
        min_items=1,
    )


def build_union_refs(
    union_model: Union_,
    build_fn: Callable[[BaseModel], BaseModel],
) -> SchemaOneOfField:
    """Union -> {oneOf: [member schemas or $refs]}."""
    members = tuple(build_fn(member) for member in union_model.union)
    return SchemaOneOfField(
        title=union_model.title, one_of=members,
        description=union_model.description,
    )


def build_verdandi_field_refs(
    field: VerdandiField,
    build_fn: Callable[[BaseModel], BaseModel],
) -> BaseModel:
    """VerdandiField -> inner type schema with $defs-aware building."""
    inner = build_fn(field.type)
    combined = concat_field_description(field)
    semantic = convert_semantic(field.semantic) if field.semantic else None
    constraint = convert_constraints(field.constraint) if field.constraint else None
    type_min = extract_type_min_length(field.type)
    override = resolve_field_min_length(field, type_min)
    if isinstance(inner, SchemaRef):
        return SchemaRef(
            ref=inner.ref, title=field.title, description=combined,
            const=field.const, default=field.default,
            min_length=override, x_semantic=semantic, x_constraint=constraint,
        )
    updates: dict[str, str | int | SchemaSemanticExt | SchemaConstraintBlock] = {
        "title": field.title, "description": combined,
    }
    if isinstance(inner, SchemaField):
        if override is not None:
            updates["min_length"] = override
        if field.const is not None:
            updates["const"] = field.const
        if field.default is not None:
            updates["default"] = field.default
    if isinstance(inner, (SchemaField, SchemaArray)):
        if semantic:
            updates["x_semantic"] = semantic
        if constraint:
            updates["x_constraint"] = constraint
    return inner.model_copy(update=updates)
