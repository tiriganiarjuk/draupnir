"""Schema building — container assembly.

CC=1-2 assemblers. Thin compositors that wire zone collectors
into SchemaObject construction.
"""

from collections.abc import Callable

from pydantic import BaseModel

from draupnir.logic.transform.schema_build.primitive import merge_zone_results
from draupnir.logic.transform.schema_build.simple import optional_tuple
from draupnir.logic.transform.zone_collect.composed import collect_conditional
from draupnir.logic.transform.zone_collect.simple import collect_required_optional
from draupnir.structure.model.complex_containers import Group
from draupnir.structure.model.schema_output import (
    SchemaConditional,
    SchemaObject,
)
from draupnir.structure.model.simple_containers import Simplegroup
from draupnir.structure.model.top_level import Section, Shallowsection


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
    build_fn: Callable[[BaseModel], BaseModel],
) -> tuple[dict[str, BaseModel], list[str], list[SchemaConditional]]:
    """Collect properties, required keys, and conditionals from a zone set.

    Handles None zone sets by returning empty collections.
    """
    if zone_set is None:
        return {}, [], []
    properties, required_keys = collect_required_optional(
        zone_set.required, zone_set.optional, build_fn,
    )
    cond_props, conditionals = collect_conditional(zone_set.conditional, build_fn)
    properties.update(cond_props)
    return properties, list(required_keys), list(conditionals)


def build_simplegroup(
    simplegroup: Simplegroup,
    build_fn: Callable[[BaseModel], BaseModel],
) -> SchemaObject:
    """Simplegroup -> {type: object, properties, required}."""
    properties, required_keys, conditionals = collect_zone_set(simplegroup, build_fn)
    return build_container_schema(
        simplegroup.title, simplegroup.description,
        properties, required_keys, conditionals,
    )


def build_group_properties(
    group: Group,
    build_fn: Callable[[BaseModel], BaseModel],
) -> tuple[dict[str, BaseModel], list[str], list[SchemaConditional]]:
    """Extract properties, required keys, and conditionals from a group."""
    return merge_zone_results(
        collect_zone_set(group.fields, build_fn),
        collect_zone_set(group.containers, build_fn),
    )


def build_group(
    group: Group,
    build_fn: Callable[[BaseModel], BaseModel],
) -> SchemaObject:
    """Group -> {type: object, properties, required, allOf?}."""
    properties, required_keys, conditionals = build_group_properties(group, build_fn)
    return build_container_schema(
        group.title, group.description,
        properties, required_keys, conditionals,
    )


def build_section(
    section: Section,
    build_fn: Callable[[BaseModel], BaseModel],
) -> SchemaObject:
    """Section -> {type: object, properties (containers only)}."""
    properties, required_keys, conditionals = collect_zone_set(section.containers, build_fn)
    return build_container_schema(
        section.title, section.description,
        properties, required_keys, conditionals,
    )


def build_shallowsection_properties(
    shallowsection: Shallowsection,
    build_fn: Callable[[BaseModel], BaseModel],
) -> tuple[dict[str, BaseModel], list[str], list[SchemaConditional]]:
    """Extract properties, required keys, and conditionals from a shallowsection."""
    return merge_zone_results(
        collect_zone_set(shallowsection.fields, build_fn),
        collect_zone_set(shallowsection.containers, build_fn),
    )


def build_shallowsection(
    shallowsection: Shallowsection,
    build_fn: Callable[[BaseModel], BaseModel],
) -> SchemaObject:
    """Shallowsection -> {type: object, fields + containers}."""
    properties, required_keys, conditionals = build_shallowsection_properties(
        shallowsection, build_fn,
    )
    return build_container_schema(
        shallowsection.title, shallowsection.description,
        properties, required_keys, conditionals,
    )
