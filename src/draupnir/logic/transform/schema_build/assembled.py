"""Schema building — container and field assembly.

CC=1-2 assemblers. Wire zone_collect and field_annotate into
SchemaObject/SchemaField construction. Each container builder follows
the same pattern: unwrap RootModel zone wrappers → collect properties
via zone_collect → merge if multiple zone sets → pass to
build_container_schema.

build_verdandi_field is the field-level assembler: it looks up the
pre-built inner type, computes field metadata (description concatenation,
min_length override, semantic/constraint extensions), then either
annotates the inline schema or builds a SchemaRef with sibling metadata
depending on whether the inner type was promoted to $defs.
"""

from pydantic import BaseModel, RootModel

from draupnir.logic.transform.field_annotate.composed import (
    apply_inline_metadata,
    compute_field_metadata,
)
from draupnir.logic.transform.schema_build.primitive import merge_zone_results
from draupnir.logic.transform.schema_build.simple import build_field_ref, optional_tuple
from draupnir.logic.transform.unwrap.simple import unwrap_zone
from draupnir.logic.transform.zone_collect.composed import collect_conditional
from draupnir.logic.transform.zone_collect.simple import collect_required_optional
from draupnir.structure.config.build_context import BuildContext
from draupnir.structure.model.schema_output import (
    SchemaConditional,
    SchemaObject,
    SchemaRef,
)


def build_container_schema(
    title: str,
    description: str,
    properties: dict[str, BaseModel],
    required_keys: list[str],
    conditionals: list[SchemaConditional],
) -> SchemaObject:
    """Build a SchemaObject with standard Verdandi container defaults.

    All container types (group, section, shallowsection, simplegroup)
    share the same output shape — this avoids duplicating SchemaObject
    construction across four builder functions.
    """
    return SchemaObject(
        title=title,
        properties=properties,
        required=optional_tuple(required_keys),
        additional_properties=False,
        all_of=optional_tuple(conditionals),
        description=description,
    )


def collect_zone_set(
    zone_set: BaseModel | None,
    context: BuildContext,
) -> tuple[dict[str, BaseModel], list[str], list[SchemaConditional]]:
    """Collect properties, required keys, and conditionals from a zone set.

    Zone sets (GroupFields, GroupContainers, etc.) have .required,
    .optional, .conditional — each wrapped in RootModel. Unwraps each
    zone dict before passing to zone_collect functions that expect plain
    dicts. Returns empty tuple for None zone sets (no fields in that zone).

    The split between collect_required_optional and collect_conditional
    exists because conditional entries carry extra when-condition data
    that produces same-section allOf entries, while required/optional
    entries only contribute to properties and required arrays.
    """
    if zone_set is None:
        return {}, [], []
    properties, required_keys = collect_required_optional(
        unwrap_zone(zone_set.required), unwrap_zone(zone_set.optional), context,
    )
    cond_props, conditionals = collect_conditional(
        unwrap_zone(zone_set.conditional), context,
    )
    properties.update(cond_props)
    return properties, list(required_keys), list(conditionals)


def build_simplegroup(model: BaseModel, context: BuildContext) -> SchemaObject:
    """Simplegroup -> SchemaObject. Has a single flat zone set (no sub-containers)."""
    properties, required_keys, conditionals = collect_zone_set(model, context)
    return build_container_schema(
        model.title.root, model.description.root,
        properties, required_keys, conditionals,
    )


def build_group(model: BaseModel, context: BuildContext) -> SchemaObject:
    """Group -> SchemaObject. Merges fields zone set + containers zone set."""
    properties, required_keys, conditionals = merge_zone_results(
        collect_zone_set(model.fields, context),
        collect_zone_set(model.containers, context),
    )
    return build_container_schema(
        model.title.root, model.description.root,
        properties, required_keys, conditionals,
    )


def build_section(model: BaseModel, context: BuildContext) -> SchemaObject:
    """Section -> SchemaObject. Sections contain only containers, no direct fields."""
    properties, required_keys, conditionals = collect_zone_set(model.containers, context)
    return build_container_schema(
        model.title.root, model.description.root,
        properties, required_keys, conditionals,
    )


def build_shallowsection(model: BaseModel, context: BuildContext) -> SchemaObject:
    """Shallowsection -> SchemaObject. Like group: merges fields + containers."""
    properties, required_keys, conditionals = merge_zone_results(
        collect_zone_set(model.fields, context),
        collect_zone_set(model.containers, context),
    )
    return build_container_schema(
        model.title.root, model.description.root,
        properties, required_keys, conditionals,
    )


def build_verdandi_field(model: BaseModel, context: BuildContext) -> BaseModel:
    """VerdandiField -> annotated inner schema or SchemaRef with metadata.

    Branches on whether the inner type was promoted to $defs:
    - SchemaRef in context.built → build_field_ref: metadata as sibling keywords
    - Inline schema in context.built → apply_inline_metadata: model_copy with updates

    Uses context.full for compute_field_metadata because it needs the actual
    inner schema's description and min_length, which are lost when the node
    becomes a SchemaRef.
    """
    inner = context.built[model.type.root]
    meta = compute_field_metadata(model, context.full[model.type.root])
    if isinstance(inner, SchemaRef):
        return build_field_ref(inner.ref, model, meta)
    return apply_inline_metadata(inner, model, meta)
