"""Schema building — dispatch functions and property extraction.

CC=4+ dispatch functions that route models to type-specific builders,
plus top-level property extraction from schema zones.

No IO. Pure model-to-model conversion.
"""

from collections.abc import Callable

from pydantic import BaseModel

from draupnir.logic.transform.field_annotate.simple import (
    concat_field_description,
    convert_constraints,
    convert_semantic,
    resolve_field_min_length,
)
from draupnir.logic.transform.schema_build.primitive import build_enum, build_simplearray
from draupnir.logic.transform.schema_build.simple import (
    build_atom,
    build_element,
    build_tuple,
    build_union,
)
from draupnir.structure.model.fields import Atom, Element, Pattern, Tuple_, Union_
from draupnir.structure.model.fields import Enum as VerdandiEnum
from draupnir.structure.model.schema_output import (
    SchemaArray,
    SchemaConstraintBlock,
    SchemaField,
    SchemaOneOfField,
    SchemaSemanticExt,
    SchemaTupleArray,
)
from draupnir.structure.model.simple_containers import (
    Simplearray,
    VerdandiField,
)
from draupnir.structure.model.top_level import SchemaSections, SchemaShallowsections


# --- Leaf dispatch (CC=5) ---


def build_field(
    model: Pattern | Atom | VerdandiEnum | Element | Union_,
) -> SchemaField | SchemaOneOfField:
    """Dispatch field model to its builder."""
    if isinstance(model, Pattern):
        return SchemaField(
            title=model.title, type="string",
            pattern=model.regex, description=model.description,
        )
    if isinstance(model, Atom):
        return build_atom(model)
    if isinstance(model, VerdandiEnum):
        return build_enum(model)
    if isinstance(model, Element):
        return build_element(model, build_field)
    return build_union(model, build_field)


# --- Simple dispatch (CC=4+) ---


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
        if field.const is not None:
            updates["const"] = field.const
        if field.default is not None:
            updates["default"] = field.default
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
        return build_tuple(model, build_field)
    if isinstance(model, Simplearray):
        return build_simplearray(model, build_simple)
    return build_field(model)


def build_schema_properties(
    zones: SchemaSections | SchemaShallowsections,
    build_or_ref_fn: Callable[..., BaseModel],
) -> tuple[dict[str, BaseModel], list[str]]:
    """Build top-level properties and required keys from schema zones."""
    properties: dict[str, BaseModel] = {}
    required_keys: list[str] = []
    if zones.required:
        for name, model_ref in zones.required.items():
            properties[name] = build_or_ref_fn(model_ref)
            required_keys.append(name)
    if zones.optional:
        for name, model_ref in zones.optional.items():
            properties[name] = build_or_ref_fn(model_ref)
    if zones.conditional:
        for name, entry in zones.conditional.items():
            properties[name] = build_or_ref_fn(entry.ref)
    return properties, required_keys
