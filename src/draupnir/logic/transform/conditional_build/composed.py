"""Conditional schema building — collectors and dispatch.

CC=4+ functions that iterate model trees to collect and dispatch
conditional schema entries. Same-section and cross-section paths.

No IO. Pure model-to-model conversion.
"""

from draupnir.logic.transform.conditional_build.simple import (
    build_root_conditional,
    resolve_cross_section_mode,
)
from draupnir.structure.model.complex_containers import Group
from draupnir.structure.model.schema_output import SchemaRootConditional
from draupnir.structure.model.top_level import (
    Schema,
    SchemaSections,
    SchemaShallowsections,
    Section,
)


def collect_group_conditionals(
    group: Group,
    group_path: tuple[str, ...],
) -> list[SchemaRootConditional]:
    """Collect cross-section conditionals from a single group."""
    results: list[SchemaRootConditional] = []
    if not group.fields or not group.fields.conditional:
        return results
    for name, entry in group.fields.conditional.items():
        resolved = resolve_cross_section_mode(
            entry.only_when, entry.always_when, entry.not_when,
        )
        if resolved is not None:
            active, mode = resolved
            results.append(build_root_conditional(active, name, group_path, mode))
    return results


def collect_section_conditionals(
    section: Section,
    section_name: str,
) -> list[SchemaRootConditional]:
    """Collect cross-section conditionals from all groups in a section."""
    results: list[SchemaRootConditional] = []
    containers = section.containers
    for zone in (containers.required, containers.optional):
        if not zone:
            continue
        for group_name, model in zone.items():
            if isinstance(model, Group):
                path = (section_name, group_name)
                results.extend(collect_group_conditionals(model, path))
    if containers.conditional:
        for group_name, entry in containers.conditional.items():
            if isinstance(entry.ref, Group):
                path = (section_name, group_name)
                results.extend(collect_group_conditionals(entry.ref, path))
    return results


def iter_schema_sections(
    schema: Schema,
) -> dict[str, Section]:
    """Iterate all section models from schema zones."""
    sections: dict[str, Section] = {}
    zones = schema.sections
    if not zones:
        return sections
    if zones.required:
        sections.update(zones.required)
    if zones.optional:
        sections.update(zones.optional)
    if zones.conditional:
        for name, entry in zones.conditional.items():
            sections[name] = entry.ref
    return sections


def collect_schema_zone_conditionals(
    zones: SchemaSections | SchemaShallowsections,
) -> list[SchemaRootConditional]:
    """Build root conditionals from the schema conditional zone."""
    results: list[SchemaRootConditional] = []
    if not zones.conditional:
        return results
    for name, entry in zones.conditional.items():
        resolved = resolve_cross_section_mode(
            entry.only_when, entry.always_when, entry.not_when,
        )
        if resolved is not None:
            active, mode = resolved
            results.append(build_root_conditional(active, name, (), mode))
    return results
