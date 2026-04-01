"""Cross-section conditional building — nested JSON Schema if/then/else.

CC=1-3. Cross-section conditionals produce allOf entries in the root
SchemaDocument. Each entry has a nested if-clause (navigating to the
source field via properties wrappers) and then/else clauses (navigating
to the target field to require or forbid it).

Three modes control the then/else shape:
  only_when: if match -> require field, else -> forbid field
  always_when: if match -> require field (no else)
  not_when: if match -> forbid field (no else)
"""

from draupnir.logic.pure.cross_section.primitive import parse_cross_section_path
from draupnir.structure.model.conditionals import ConditionalWhen
from draupnir.structure.model.schema_output import (
    NestedPathProperties,
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
    """Return the first non-None when via short-circuit or.

    Exactly one of the three is set per conditional entry (enforced
    by the input JSON Schema). The or-chain finds it without branching.
    """
    return only_when or always_when or not_when


def conditional_mode_name(
    only_when: ConditionalWhen | None,
    always_when: ConditionalWhen | None,
) -> str:
    """Determine the mode string by checking which when is truthy.

    Mode drives the then/else shape downstream: only_when produces
    both then + else, always_when produces then only, not_when
    produces then with the else content (inverted logic).
    """
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
    """Gate: only proceed if the active when targets a cross-section path.

    Returns None for same-section conditionals (no leading dot) — those
    are handled by transform/conditional_build. Returns (when, mode) for
    cross-section so the caller can build nested if/then/else structures.
    """
    active = resolve_active_when(only_when, always_when, not_when)
    if active is None or not active.field.startswith("."):
        return None
    return active, conditional_mode_name(only_when, always_when)


def build_value_constraint(when: ConditionalWhen) -> SchemaConst | SchemaEnumConstraint:
    """Map the predicate type to its JSON Schema equivalent.

    equals -> {"const": value}, in_ -> {"enum": [values]}.
    """
    if when.equals is not None:
        return SchemaConst(const=when.equals)
    return SchemaEnumConstraint(enum=when.in_)


def wrap_nested_path(
    segments: tuple[str, ...],
    leaf: SchemaNestedPath,
) -> SchemaNestedPath:
    """Build inside-out: wrap the leaf in successive properties layers.

    Reversed iteration so the outermost segment wraps last. This produces
    the nested {"properties": {"task": {"properties": {"processing": ...}}}}
    structure that JSON Schema uses for deep property navigation.
    """
    result = leaf
    for segment in reversed(segments):
        result = SchemaNestedPath(
            properties=NestedPathProperties({segment: result}),
        )
    return result


def build_if_nested(when: ConditionalWhen) -> SchemaNestedPath:
    """Parse the dotted field path and wrap the constraint in nested properties.

    Branches on when.exists: existence checks produce {"required": [field]},
    value checks produce {"properties": {field: constraint}, "required": [field]}.
    """
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
    """Compose if + then + else clauses based on the conditional mode.

    target_path is the (section_name, group_name) chain to the field being
    controlled. The mode determines the then/else shape — see module docstring.
    """
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
