"""Standalone simple container converters.

Converts Tuple, Simplearray, VerdandiField, Simplegroup into JSON Schema
output models. Composes field converters from converters.field. These are
$defs-unaware — they produce inline schemas for testing and composition.

No IO. Pure model-to-model conversion.
"""

from pydantic import BaseModel

from draupnir.functions.pure.converters.extension import (
    concat_field_description,
    convert_constraints,
    convert_semantic,
    resolve_field_min_length,
)
from draupnir.functions.pure.converters.field import build_field
from draupnir.functions.pure.converters.zone import (
    collect_conditional,
    collect_required_optional,
)
from draupnir.structures.schema_output import (
    SchemaArray,
    SchemaConstraintBlock,
    SchemaField,
    SchemaObject,
    SchemaOneOfField,
    SchemaSemanticExt,
    SchemaTupleArray,
)
from draupnir.structures.simple_containers import (
    Simplearray,
    Simplegroup,
    Tuple_,
    VerdandiField,
)


def build_tuple(tuple_model: Tuple_) -> SchemaTupleArray:
    """Tuple -> {prefixItems: [...], items: false}."""
    prefix = tuple(build_field(item) for item in tuple_model.items)
    return SchemaTupleArray(
        title=tuple_model.title,
        prefix_items=prefix,
        description=tuple_model.description,
        min_items=len(prefix),
        max_items=len(prefix),
    )


def build_simplearray(simplearray: Simplearray) -> SchemaArray:
    """Simplearray -> {type: array, items: {field}}."""
    return SchemaArray(
        title=simplearray.title,
        items=build_simple(simplearray.items),
        description=simplearray.description,
        min_items=1,
    )


def build_verdandi_field(
    field: VerdandiField,
) -> SchemaField | SchemaOneOfField | SchemaTupleArray | SchemaArray:
    """VerdandiField -> inner type schema with description + extensions."""
    inner = build_simple(field.type)
    combined = concat_field_description(field)
    updates: dict[str, str | int | SchemaSemanticExt | SchemaConstraintBlock] = {
        "title": field.title,
        "description": combined,
    }
    if isinstance(inner, SchemaField):
        override = resolve_field_min_length(field, inner.min_length)
        if override is not None:
            updates["min_length"] = override
    if isinstance(inner, (SchemaField, SchemaArray)):
        if field.semantic:
            updates["x_semantic"] = convert_semantic(field.semantic)
        if field.constraint:
            updates["x_constraint"] = convert_constraints(field.constraint)
    return inner.model_copy(update=updates)


def build_simple(
    model: BaseModel,
) -> SchemaField | SchemaOneOfField | SchemaTupleArray | SchemaArray:
    """Dispatch field or simple container to its builder."""
    if isinstance(model, VerdandiField):
        return build_verdandi_field(model)
    if isinstance(model, Tuple_):
        return build_tuple(model)
    if isinstance(model, Simplearray):
        return build_simplearray(model)
    return build_field(model)


def build_simplegroup(simplegroup: Simplegroup) -> SchemaObject:
    """Simplegroup -> {type: object, properties, required}."""
    properties, required_keys = collect_required_optional(
        simplegroup.required, simplegroup.optional, build_simple,
    )
    cond_props, conditionals = collect_conditional(
        simplegroup.conditional, build_simple,
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
