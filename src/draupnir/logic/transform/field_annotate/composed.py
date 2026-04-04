"""Field annotation — metadata application.

CC=4-8 functions that apply Verdandi field-level metadata onto built
JSON Schema nodes. The complexity comes from the two application paths:

apply_inline_metadata: patches an inline schema via model_copy(update=...).
  Different schema types accept different subsets of metadata — SchemaField
  gets min_length/const/default, SchemaArray gets semantic/constraint,
  SchemaOneOfField gets default only. The isinstance branches gate this.

compute_field_metadata: assembles a FieldMeta from the field model and
  its resolved inner type schema. This is where description concatenation,
  min_length override resolution, and semantic/constraint conversion
  all happen — producing a single FieldMeta that both apply_inline_metadata
  and build_field_ref (simple.py) consume.
"""

from pydantic import BaseModel

from draupnir.logic.transform.field_annotate.simple import (
    concat_field_description,
    convert_constraints,
    convert_semantic,
    default_override,
    extension_overrides,
    extract_type_max_length,
    extract_type_min_length,
    field_overrides,
    resolve_field_max_length,
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

    Uses model_copy(update=...) to non-destructively add field-level
    metadata to the already-built inner schema. The isinstance branches
    gate which updates apply to which schema types:
    - SchemaField/SchemaOneOfField: can carry defaults
    - SchemaField only: can carry min_length and const overrides
    - SchemaField/SchemaArray: can carry semantic and constraint extensions
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
    """Compute combined field metadata from the field model and its type schema.

    Assembles a FieldMeta by resolving the interaction between field-level
    and type-level properties:
    - Description: concatenated (field first, type second) unless identical
    - min_length: field value only overrides when it exceeds the type floor
    - Semantic: converted from Verdandi SemanticBlock to SchemaSemanticExt
    - Constraint: converted from Verdandi ConstraintRules to SchemaConstraintBlock

    inner_schema is context.full[field.type.root] — the complete built schema
    for the referenced type, needed for its description and min_length values.
    """
    field_description = field_model.description.root
    type_desc = inner_schema.description if hasattr(inner_schema, "description") else None
    combined = concat_field_description(field_description, type_desc)
    semantic = convert_semantic(field_model.semantic) if field_model.semantic else None
    field_min = field_model.min_length.root if field_model.min_length else None
    type_min = extract_type_min_length(inner_schema)
    min_override = resolve_field_min_length(field_min, type_min)
    field_max = field_model.max_length.root if field_model.max_length else None
    type_max = extract_type_max_length(inner_schema)
    max_override = resolve_field_max_length(field_max, type_max)
    constraint_entries = convert_constraints(field_model.constraint) if field_model.constraint else None
    constraint = SchemaConstraintBlock(constraints=constraint_entries) if constraint_entries else None
    return FieldMeta(
        description=combined, min_length=min_override, max_length=max_override,
        semantic=semantic, constraint=constraint,
    )
