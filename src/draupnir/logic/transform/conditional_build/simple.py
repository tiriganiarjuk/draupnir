"""Same-section conditional schema building — branching builders.

CC=1-3. Called during schema_build to produce SchemaConditional nodes
for fields with when-conditions that reference fields in the SAME section.
Cross-section conditionals (field paths starting with ".") are filtered
out here and handled separately by pure/cross_section/ at graph traversal time.

The entry point is build_conditional_entry, called by zone_collect/composed.py
for each conditional zone dict entry. It resolves which when is active,
gates on same-section, builds the if-clause, and dispatches to the
appropriate primitive builder based on mode.
"""

from draupnir.logic.transform.conditional_build.primitive import (
    build_always_when,
    build_not_when,
    build_only_when,
)
from draupnir.structure.model.conditionals import ConditionalWhen
from draupnir.structure.model.schema_output import (
    SchemaCondition,
    SchemaConditional,
    SchemaConst,
    SchemaEnumConstraint,
)


def resolve_active_when(
    only_when: ConditionalWhen | None,
    always_when: ConditionalWhen | None,
    not_when: ConditionalWhen | None,
) -> ConditionalWhen | None:
    """Return whichever conditional when is set, or None."""
    return only_when or always_when or not_when


def is_cross_section(when: ConditionalWhen | None) -> bool:
    """Check if a conditional references a cross-section field path."""
    return when is not None and when.field.startswith(".")


def build_value_constraint(when: ConditionalWhen) -> SchemaConst | SchemaEnumConstraint:
    """Build a value constraint: equals->const, in_->enum."""
    if when.equals is not None:
        return SchemaConst(const=when.equals)
    return SchemaEnumConstraint(enum=when.in_)


def build_if_condition(when: ConditionalWhen) -> SchemaCondition:
    """Build the if-clause from a ConditionalWhen."""
    if when.exists:
        return SchemaCondition(required=(when.field,))
    constraint = build_value_constraint(when)
    return SchemaCondition(properties={when.field: constraint}, required=(when.field,))


def dispatch_when_builder(
    field_name: str,
    if_clause: SchemaCondition,
    only_when: ConditionalWhen | None,
    always_when: ConditionalWhen | None,
) -> SchemaConditional:
    """Dispatch to the correct when builder based on which condition is set."""
    if only_when:
        return build_only_when(field_name, if_clause)
    if always_when:
        return build_always_when(field_name, if_clause)
    return build_not_when(field_name, if_clause)


def build_conditional_entry(
    field_name: str,
    only_when: ConditionalWhen | None,
    always_when: ConditionalWhen | None,
    not_when: ConditionalWhen | None,
) -> SchemaConditional | None:
    """Build if/then/else from conditional when values.

    Returns None for cross-section conditionals (dotted field paths).
    """
    active = resolve_active_when(only_when, always_when, not_when)
    if active is None or is_cross_section(active):
        return None
    if_clause = build_if_condition(active)
    return dispatch_when_builder(field_name, if_clause, only_when, always_when)
