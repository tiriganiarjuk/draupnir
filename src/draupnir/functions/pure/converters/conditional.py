"""Conditional schema converters for if/then/else logic.

Converts ConditionalWhen predicates into JSON Schema conditional
blocks (if/then/else). Cross-section conditionals (dotted field paths)
return None here and are hoisted to root level by the exporter.

No IO. Pure model-to-model conversion.
"""

from draupnir.structures.conditionals import ConditionalWhen
from draupnir.structures.schema_output import (
    SchemaCondition,
    SchemaConditional,
    SchemaConst,
    SchemaEnumConstraint,
)


def build_if_condition(when: ConditionalWhen) -> SchemaCondition:
    """Build the if-clause from a ConditionalWhen."""
    if when.equals is not None:
        constraint: SchemaConst | SchemaEnumConstraint = SchemaConst(const=when.equals)
    else:
        constraint = SchemaEnumConstraint(enum=when.in_)
    return SchemaCondition(properties={when.field: constraint})


def is_cross_section(when: ConditionalWhen | None) -> bool:
    """Check if a conditional references a cross-section field path."""
    return when is not None and "." in when.field


def build_only_when(field_name: str, when: ConditionalWhen) -> SchemaConditional:
    """only_when: required when true, forbidden when false."""
    return SchemaConditional(
        if_=build_if_condition(when),
        then_=SchemaCondition(required=(field_name,)),
        else_=SchemaCondition(properties={field_name: False}),
    )


def build_always_when(field_name: str, when: ConditionalWhen) -> SchemaConditional:
    """always_when: required when true, no effect when false."""
    return SchemaConditional(
        if_=build_if_condition(when),
        then_=SchemaCondition(required=(field_name,)),
    )


def build_not_when(field_name: str, when: ConditionalWhen) -> SchemaConditional:
    """not_when: forbidden when true, no effect when false."""
    return SchemaConditional(
        if_=build_if_condition(when),
        then_=SchemaCondition(properties={field_name: False}),
    )


def build_conditional_entry(
    field_name: str,
    only_when: ConditionalWhen | None,
    always_when: ConditionalWhen | None,
    not_when: ConditionalWhen | None,
) -> SchemaConditional | None:
    """Build if/then/else from conditional when values.

    Returns None for cross-section conditionals (dotted field paths).
    These are hoisted to root level by the exporter.
    """
    active = only_when or always_when or not_when
    if active is None or is_cross_section(active):
        return None
    if only_when:
        return build_only_when(field_name, only_when)
    if always_when:
        return build_always_when(field_name, always_when)
    return build_not_when(field_name, not_when)
