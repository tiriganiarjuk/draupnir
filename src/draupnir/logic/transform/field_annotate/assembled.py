"""Field annotation — VerdandiField assembly.

CC=1-2 assemblers. Wire field metadata computation with
type-specific metadata application.
"""

from collections.abc import Callable

from pydantic import BaseModel

from draupnir.logic.transform.field_annotate.composed import apply_inline_metadata
from draupnir.logic.transform.field_annotate.simple import compute_field_metadata
from draupnir.structure.model.schema_output import SchemaRef
from draupnir.structure.model.simple_containers import VerdandiField


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
    return apply_inline_metadata(inner, field, meta)
