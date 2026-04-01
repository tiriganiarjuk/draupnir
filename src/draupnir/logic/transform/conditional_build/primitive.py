"""Same-section conditional schema building — if/then/else node constructors.

CC=1. These produce the SchemaConditional nodes that appear inside section
and group schemas (NOT the root allOf entries — those are cross-section
and handled by pure/cross_section/). Each mode maps to a different
JSON Schema if/then/else shape:
  only_when: then=required, else=forbidden (properties: {field: false})
  always_when: then=required, no else
  not_when: then=forbidden, no else
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
