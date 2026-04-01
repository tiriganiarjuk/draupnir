"""Conditional schema building — single-expression constructors.

CC=1 builders for conditional schema nodes. No branching.
"""

from draupnir.structure.model.schema_output import (
    SchemaCondition,
    SchemaConditional,
)


def build_only_when(field_name: str, if_clause: SchemaCondition) -> SchemaConditional:
    """only_when: required when true, forbidden when false."""
    return SchemaConditional(
        if_=if_clause,
        then_=SchemaCondition(required=(field_name,)),
        else_=SchemaCondition(properties={field_name: False}),
    )


def build_always_when(field_name: str, if_clause: SchemaCondition) -> SchemaConditional:
    """always_when: required when true, no effect when false."""
    return SchemaConditional(
        if_=if_clause,
        then_=SchemaCondition(required=(field_name,)),
    )


def build_not_when(field_name: str, if_clause: SchemaCondition) -> SchemaConditional:
    """not_when: forbidden when true, no effect when false."""
    return SchemaConditional(
        if_=if_clause,
        then_=SchemaCondition(properties={field_name: False}),
    )


def strip_cross_section_marker(field_path: str) -> str:
    """Remove leading dot from cross-section field path."""
    return field_path.lstrip(".")


def split_dotted_path(path: str) -> tuple[tuple[str, ...], str]:
    """Split dotted path into (parent_segments, leaf_name)."""
    segments = tuple(path.split("."))
    return segments[:-1], segments[-1]


def parse_cross_section_path(field_path: str) -> tuple[tuple[str, ...], str]:
    """Parse cross-section path: '.a.b.c' -> (('a', 'b'), 'c')."""
    return split_dotted_path(strip_cross_section_marker(field_path))
