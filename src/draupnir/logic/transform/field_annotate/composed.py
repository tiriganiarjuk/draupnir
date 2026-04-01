"""Field annotation — metadata application.

CC=4-8 functions. Applies field-level metadata to JSON Schema nodes
and computes field metadata from built inner schemas.

No IO. Pure model-to-model conversion.
"""

from pydantic import BaseModel

from draupnir.logic.transform.field_annotate.simple import (
    concat_field_description,
    convert_constraints,
    convert_semantic,
    default_override,
    extension_overrides,
    extract_type_min_length,
    field_overrides,
    resolve_field_min_length,
    unwrap_string_or_none,
)
from draupnir.structure.model.schema_output import (
    FieldMeta,
    SchemaArray,
    SchemaConstraintBlock,
    SchemaField,
    SchemaOneOfField,
    SchemaSemanticExt,
)


def apply_inline_metadata(
    inner: BaseModel,
    field_model: BaseModel,
    meta: FieldMeta,
) -> BaseModel:
    """Apply field metadata to an inline (non-$ref) schema node.

    field_model is a generated VerdandiField input model with RootModel
    wrapper fields (.title.root, .default.root, .const.root).
    """
    default_value = field_model.default.root if field_model.default else None
    field_const = unwrap_string_or_none(field_model.const)
    updates: dict[str, str | int | SchemaSemanticExt | SchemaConstraintBlock] = {
        "title": field_model.title.root, "description": meta.description,
    }
    if isinstance(inner, (SchemaField, SchemaOneOfField)):
        updates.update(default_override(default_value))
    if isinstance(inner, SchemaField):
        updates.update(field_overrides(meta.min_length, field_const, meta))
    if isinstance(inner, (SchemaField, SchemaArray)):
        updates.update(extension_overrides(meta))
    return inner.model_copy(update=updates)


def compute_field_metadata(
    field_model: BaseModel,
    inner_schema: BaseModel,
) -> FieldMeta:
    """Compute description, min_length override, semantic, and constraint.

    field_model: generated VerdandiField input model
    inner_schema: context.full[field.type.root] — the built type schema
    """
    field_description = field_model.description.root
    type_desc = inner_schema.description if hasattr(inner_schema, "description") else None
    combined = concat_field_description(field_description, type_desc)
    semantic = convert_semantic(field_model.semantic) if field_model.semantic else None
    field_min = field_model.min_length.root if field_model.min_length else None
    type_min = extract_type_min_length(inner_schema)
    override = resolve_field_min_length(field_min, type_min)
    constraint_entries = convert_constraints(field_model.constraint) if field_model.constraint else None
    constraint = SchemaConstraintBlock(constraints=constraint_entries) if constraint_entries else None
    return FieldMeta(
        description=combined, min_length=override,
        semantic=semantic, constraint=constraint,
    )
