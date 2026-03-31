"""Field annotation — metadata application.

CC=4+ functions. Applies field-level metadata to JSON Schema nodes.

No IO. Pure model-to-model conversion.
"""

from collections.abc import Callable

from pydantic import BaseModel

from draupnir.logic.transform.field_annotate.simple import (
    default_override,
    extension_overrides,
    field_overrides,
)
from draupnir.structure.model.schema_output import (
    FieldMeta,
    SchemaArray,
    SchemaConstraintBlock,
    SchemaField,
    SchemaOneOfField,
    SchemaSemanticExt,
)
from draupnir.structure.model.simple_containers import VerdandiField


def apply_inline_metadata(
    inner: BaseModel,
    field: VerdandiField,
    meta: FieldMeta,
) -> BaseModel:
    """Apply field metadata to an inline (non-$ref) schema node."""
    updates: dict[str, str | int | SchemaSemanticExt | SchemaConstraintBlock] = {
        "title": field.title, "description": meta.description,
    }
    if isinstance(inner, (SchemaField, SchemaOneOfField)):
        updates.update(default_override(field))
    if isinstance(inner, SchemaField):
        updates.update(field_overrides(field, meta))
    if isinstance(inner, (SchemaField, SchemaArray)):
        updates.update(extension_overrides(meta))
    return inner.model_copy(update=updates)
