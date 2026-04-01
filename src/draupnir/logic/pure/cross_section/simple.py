"""Cross-section conditional building — branching builders.

CC=1-3. Resolves active when-conditions, builds nested if/then/else
structures for cross-section conditional schema entries.
"""

from pydantic import BaseModel

from draupnir.logic.pure.cross_section.primitive import parse_cross_section_path
from draupnir.structure.model.conditionals import ConditionalWhen
from draupnir.structure.model.schema_output import (
    NestedPathProperties,
    SchemaConst,
    SchemaEnumConstraint,
    SchemaNestedPath,
    SchemaRootConditional,
)


def unwrap_when_equals(when_inner: BaseModel) -> str | int | bool | None:
    """Extract equals value from a generated ConditionalWhen inner model."""
    return when_inner.equals.root if when_inner.equals else None


def unwrap_when_in_values(
    when_inner: BaseModel,
) -> tuple[str | int | bool, ...] | None:
    """Extract in_ values as tuple from a generated ConditionalWhen inner model."""
    values_list = when_inner.in_.root if when_inner.in_ else None
    return tuple(values_list) if values_list else None


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


def build_value_constraint(when: ConditionalWhen) -> SchemaConst | SchemaEnumConstraint:
    """Build a value constraint: equals->const, in_->enum."""
    if when.equals is not None:
        return SchemaConst(const=when.equals)
    return SchemaEnumConstraint(enum=when.in_)


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
