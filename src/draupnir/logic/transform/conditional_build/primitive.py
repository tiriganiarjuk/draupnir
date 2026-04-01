"""Same-section conditional schema building — single-expression constructors.

CC=1. Builds if/then/else schema nodes for same-section conditional entries.
No branching.
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
