"""VerdandiField metadata application.

Computes field metadata (description, min_length, semantic, constraint)
and applies it to already-built inner schemas. Handles both $ref pointers
(new SchemaRef with metadata) and inline schemas (model_copy with
type-conditional updates).

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
from draupnir.structures.schema_output import (
    FieldMeta,
    SchemaArray,
    SchemaConstraintBlock,
    SchemaField,
    SchemaOneOfField,
    SchemaRef,
    SchemaSemanticExt,
)
from draupnir.structures.simple_containers import VerdandiField


def compute_field_metadata(field: VerdandiField) -> FieldMeta:
    """Compute description, min_length override, semantic, and constraint."""
    combined = concat_field_description(field)
    semantic = convert_semantic(field.semantic) if field.semantic else None
    constraint = convert_constraints(field.constraint) if field.constraint else None
    type_min = extract_type_min_length(field.type)
    override = resolve_field_min_length(field, type_min)
    return FieldMeta(
        description=combined, min_length=override,
        semantic=semantic, constraint=constraint,
    )


def build_verdandi_field_refs(
    field: VerdandiField,
    build_fn: Callable[[BaseModel], BaseModel],
) -> BaseModel:
    """VerdandiField -> inner type schema with $defs-aware building."""
    inner = build_fn(field.type)
    meta = compute_field_metadata(field)
    if isinstance(inner, SchemaRef):
        return SchemaRef(
            ref=inner.ref, title=field.title, description=meta.description,
            const=field.const, default=field.default,
            min_length=meta.min_length, x_semantic=meta.semantic,
            x_constraint=meta.constraint,
        )
    updates: dict[str, str | int | SchemaSemanticExt | SchemaConstraintBlock] = {
        "title": field.title, "description": meta.description,
    }
    if isinstance(inner, (SchemaField, SchemaOneOfField)):
        if field.default is not None:
            updates["default"] = field.default
    if isinstance(inner, SchemaField):
        if meta.min_length is not None:
            updates["min_length"] = meta.min_length
        if field.const is not None:
            updates["const"] = field.const
    if isinstance(inner, (SchemaField, SchemaArray)):
        if meta.semantic:
            updates["x_semantic"] = meta.semantic
        if meta.constraint:
            updates["x_constraint"] = meta.constraint
    return inner.model_copy(update=updates)
