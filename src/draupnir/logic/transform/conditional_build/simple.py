"""Conditional schema building — branching builders.

CC=2-3 builders. Each has a small number of branches for
condition type dispatch or path parsing.
"""

from draupnir.logic.transform.conditional_build.primitive import (
    build_always_when,
    build_not_when,
    build_only_when,
    parse_cross_section_path,
)
from draupnir.structure.model.conditionals import ConditionalWhen
from draupnir.structure.model.schema_output import (
    NestedPathProperties,
    SchemaCondition,
    SchemaConditional,
    SchemaConst,
    SchemaEnumConstraint,
    SchemaNestedPath,
    SchemaRootConditional,
)


def resolve_active_when(
    only_when: ConditionalWhen | None,
    always_when: ConditionalWhen | None,
    not_when: ConditionalWhen | None,
) -> ConditionalWhen | None:
    """Return whichever conditional when is set, or None."""
    return only_when or always_when or not_when


def conditional_mode_name(
    only_when: ConditionalWhen | None,
    always_when: ConditionalWhen | None,
) -> str:
    """Return the mode string for whichever conditional is set."""
    if only_when:
        return "only_when"
    if always_when:
        return "always_when"
    return "not_when"


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


def resolve_cross_section_mode(
    only_when: ConditionalWhen | None,
    always_when: ConditionalWhen | None,
    not_when: ConditionalWhen | None,
) -> tuple[ConditionalWhen, str] | None:
    """Resolve active cross-section conditional and its mode.

    Returns (active_when, mode_string) if cross-section, None otherwise.
    """
    active = resolve_active_when(only_when, always_when, not_when)
    if active is None or not active.field.startswith("."):
        return None
    return active, conditional_mode_name(only_when, always_when)


def is_cross_section(when: ConditionalWhen | None) -> bool:
    """Check if a conditional references a cross-section field path."""
    return when is not None and when.field.startswith(".")


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


def build_value_constraint(when: ConditionalWhen) -> SchemaConst | SchemaEnumConstraint:
    """Build a value constraint: equals→const, in_→enum."""
    if when.equals is not None:
        return SchemaConst(const=when.equals)
    return SchemaEnumConstraint(enum=when.in_)


def build_if_condition(when: ConditionalWhen) -> SchemaCondition:
    """Build the if-clause from a ConditionalWhen."""
    if when.exists:
        return SchemaCondition(required=(when.field,))
    constraint = build_value_constraint(when)
    return SchemaCondition(properties={when.field: constraint}, required=(when.field,))


def wrap_nested_path(
    segments: tuple[str, ...],
    leaf: SchemaNestedPath,
) -> SchemaNestedPath:
    """Wrap a leaf SchemaNestedPath in nested property segments."""
    result = leaf
    for segment in reversed(segments):
        result = SchemaNestedPath(
            properties=NestedPathProperties({segment: result}),
        )
    return result


def build_if_nested(when: ConditionalWhen) -> SchemaNestedPath:
    """Build nested if-clause from a cross-section ConditionalWhen."""
    path_segments, field_name = parse_cross_section_path(when.field)
    if when.exists:
        leaf = SchemaNestedPath(required=(field_name,))
    else:
        constraint = build_value_constraint(when)
        leaf = SchemaNestedPath(
            properties=NestedPathProperties({field_name: constraint}),
            required=(field_name,),
        )
    return wrap_nested_path(path_segments, leaf)


def build_then_nested(
    target_path: tuple[str, ...],
    field_name: str,
) -> SchemaNestedPath:
    """Build nested then-clause: require field at target path."""
    leaf = SchemaNestedPath(required=(field_name,))
    return wrap_nested_path(target_path, leaf)


def build_else_nested(
    target_path: tuple[str, ...],
    field_name: str,
) -> SchemaNestedPath:
    """Build nested else-clause: forbid field at target path."""
    leaf = SchemaNestedPath(
        properties=NestedPathProperties({field_name: False}),
    )
    return wrap_nested_path(target_path, leaf)


def build_root_conditional(
    when: ConditionalWhen,
    field_name: str,
    target_path: tuple[str, ...],
    mode: str,
) -> SchemaRootConditional:
    """Build one SchemaRootConditional from a cross-section conditional."""
    if_clause = build_if_nested(when)
    if mode == "only_when":
        return SchemaRootConditional(
            if_=if_clause,
            then_=build_then_nested(target_path, field_name),
            else_=build_else_nested(target_path, field_name),
        )
    if mode == "always_when":
        return SchemaRootConditional(
            if_=if_clause,
            then_=build_then_nested(target_path, field_name),
        )
    return SchemaRootConditional(
        if_=if_clause,
        then_=build_else_nested(target_path, field_name),
    )
