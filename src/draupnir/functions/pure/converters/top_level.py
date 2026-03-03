"""Top-level and group converters for Section, Shallowsection, Group.

Receives a build function (closure over $defs context) from the
dispatcher. Uses zone collection primitives for required/optional/
conditional zones.

No IO. Pure model-to-model conversion.
"""

from collections.abc import Callable

from pydantic import BaseModel

from draupnir.functions.pure.converters.zone import (
    collect_conditional,
    collect_required_optional,
)
from draupnir.structures.complex_containers import Group
from draupnir.structures.schema_output import SchemaConditional, SchemaObject
from draupnir.structures.top_level import Section, Shallowsection


def build_group_properties(
    group: Group,
    build_fn: Callable[[BaseModel], BaseModel],
) -> tuple[dict[str, BaseModel], list[str], list[SchemaConditional]]:
    """Extract properties, required keys, and conditionals from a group."""
    properties: dict[str, BaseModel] = {}
    required_keys: list[str] = []
    conditionals: list[SchemaConditional] = []
    if group.fields:
        props, req = collect_required_optional(
            group.fields.required, group.fields.optional, build_fn,
        )
        properties.update(props)
        required_keys.extend(req)
        cond_props, conds = collect_conditional(group.fields.conditional, build_fn)
        properties.update(cond_props)
        conditionals.extend(conds)
    if group.containers:
        props, req = collect_required_optional(
            group.containers.required, group.containers.optional, build_fn,
        )
        properties.update(props)
        required_keys.extend(req)
        cond_props, conds = collect_conditional(group.containers.conditional, build_fn)
        properties.update(cond_props)
        conditionals.extend(conds)
    return properties, required_keys, conditionals


def build_group(
    group: Group,
    build_fn: Callable[[BaseModel], BaseModel],
) -> SchemaObject:
    """Group -> {type: object, properties, required, allOf?}."""
    properties, required_keys, conditionals = build_group_properties(group, build_fn)
    return SchemaObject(
        title=group.title,
        properties=properties,
        required=tuple(required_keys) if required_keys else None,
        additional_properties=False,
        all_of=tuple(conditionals) if conditionals else None,
        description=group.description,
    )


def build_section(
    section: Section,
    build_fn: Callable[[BaseModel], BaseModel],
) -> SchemaObject:
    """Section -> {type: object, properties (containers only)}."""
    properties, required_keys = collect_required_optional(
        section.containers.required, section.containers.optional, build_fn,
    )
    return SchemaObject(
        title=section.title,
        properties=properties,
        required=tuple(required_keys) if required_keys else None,
        additional_properties=False,
        description=section.description,
    )


def build_shallowsection(
    shallowsection: Shallowsection,
    build_fn: Callable[[BaseModel], BaseModel],
) -> SchemaObject:
    """Shallowsection -> {type: object, fields + containers}."""
    properties, required_keys = collect_required_optional(
        shallowsection.required, shallowsection.optional, build_fn,
    )
    cond_props, conditionals = collect_conditional(
        shallowsection.conditional, build_fn,
    )
    properties.update(cond_props)
    if shallowsection.containers:
        cont_props, cont_required = collect_required_optional(
            shallowsection.containers.required,
            shallowsection.containers.optional,
            build_fn,
        )
        properties.update(cont_props)
        required_keys.extend(cont_required)
    return SchemaObject(
        title=shallowsection.title,
        properties=properties,
        required=tuple(required_keys) if required_keys else None,
        additional_properties=False,
        all_of=tuple(conditionals) if conditionals else None,
        description=shallowsection.description,
    )
