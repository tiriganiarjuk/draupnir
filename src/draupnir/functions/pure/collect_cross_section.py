"""Cross-section conditional collectors.

Walks Verdandi Schema, Section, and Group models to find conditionals
with leading-dot field paths. Delegates building to
build_cross_section.build_root_conditional.

No IO. Pure model traversal.
"""

from draupnir.functions.pure.build_cross_section import (
    build_root_conditional,
    collect_group_conditionals,
)
from draupnir.structures.complex_containers import Group
from draupnir.structures.schema_output import SchemaRootConditional
from draupnir.structures.top_level import Schema, Section


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


def collect_schema_conditionals(
    schema: Schema,
) -> tuple[SchemaRootConditional, ...] | None:
    """Collect all cross-section conditionals from a Schema."""
    results: list[SchemaRootConditional] = []
    for name, section in iter_schema_sections(schema).items():
        results.extend(collect_section_conditionals(section, name))
    if not results:
        return None
    return tuple(results)
