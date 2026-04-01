"""Schema building — container and field assembly.

CC=1-2 assemblers. Thin compositors that wire zone collectors and
field annotators into SchemaObject/SchemaField construction. Unwraps
RootModel zone wrappers from generated input models.
"""

from pydantic import BaseModel, RootModel

from draupnir.logic.transform.field_annotate.composed import (
    apply_inline_metadata,
    compute_field_metadata,
)
from draupnir.logic.transform.schema_build.primitive import merge_zone_results
from draupnir.logic.transform.schema_build.simple import build_field_ref, optional_tuple, unwrap_zone
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
    """Build a SchemaObject for any container type with standard defaults."""
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
    .optional, .conditional — each wrapped in RootModel. Unwrap before
    passing to zone_collect functions.
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
    """Simplegroup -> {type: object, properties, required}."""
    properties, required_keys, conditionals = collect_zone_set(model, context)
    return build_container_schema(
        model.title.root, model.description.root,
        properties, required_keys, conditionals,
    )


def build_group(model: BaseModel, context: BuildContext) -> SchemaObject:
    """Group -> {type: object, properties, required, allOf?}."""
    properties, required_keys, conditionals = merge_zone_results(
        collect_zone_set(model.fields, context),
        collect_zone_set(model.containers, context),
    )
    return build_container_schema(
        model.title.root, model.description.root,
        properties, required_keys, conditionals,
    )


def build_section(model: BaseModel, context: BuildContext) -> SchemaObject:
    """Section -> {type: object, properties (containers only)}."""
    properties, required_keys, conditionals = collect_zone_set(model.containers, context)
    return build_container_schema(
        model.title.root, model.description.root,
        properties, required_keys, conditionals,
    )


def build_shallowsection(model: BaseModel, context: BuildContext) -> SchemaObject:
    """Shallowsection -> {type: object, fields + containers}."""
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

    Looks up the built inner type schema, computes field metadata,
    then delegates to build_field_ref (shared) or apply_inline_metadata.
    """
    inner = context.built[model.type.root]
    meta = compute_field_metadata(model, context.full[model.type.root])
    if isinstance(inner, SchemaRef):
        return build_field_ref(inner.ref, model, meta)
    return apply_inline_metadata(inner, model, meta)
