"""Cross-section conditional builder.

Walks Verdandi Schema models to find conditionals with dotted field
paths (e.g. 'task.processing.processing_output_file_name_known').
Builds SchemaRootConditional entries with nested property paths for
placement at the root allOf of the SchemaDocument.

No IO. Pure model traversal and construction.
"""

from draupnir.structures.conditionals import ConditionalWhen
from draupnir.structures.complex_containers import Group
from draupnir.structures.schema_output import (
    NestedPathProperties,
    SchemaConst,
    SchemaEnumConstraint,
    SchemaNestedPath,
    SchemaRootConditional,
)


def wrap_nested_path(
    segments: tuple[str, ...],
    leaf: SchemaNestedPath,
) -> SchemaNestedPath:
    """Wrap a leaf SchemaNestedPath in nested property segments.

    ('task', 'processing') + leaf ->
    SchemaNestedPath(properties={'task': SchemaNestedPath(
        properties={'processing': leaf})})
    """
    result = leaf
    for segment in reversed(segments):
        result = SchemaNestedPath(
            properties=NestedPathProperties({segment: result}),
        )
    return result


def build_if_nested(when: ConditionalWhen) -> SchemaNestedPath:
    """Build nested if-clause from a cross-section ConditionalWhen."""
    path = when.field.lstrip(".")
    segments = tuple(path.split("."))
    field_name = segments[-1]
    path_segments = segments[:-1]
    if when.exists:
        leaf = SchemaNestedPath(required=(field_name,))
    elif when.equals is not None:
        constraint: SchemaConst | SchemaEnumConstraint = SchemaConst(const=when.equals)
        leaf = SchemaNestedPath(
            properties=NestedPathProperties({field_name: constraint}),
        )
    else:
        constraint = SchemaEnumConstraint(enum=when.in_)
        leaf = SchemaNestedPath(
            properties=NestedPathProperties({field_name: constraint}),
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
    """Build one SchemaRootConditional from a cross-section conditional.

    mode is 'only_when', 'always_when', or 'not_when'.
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


def collect_group_conditionals(
    group: Group,
    group_path: tuple[str, ...],
) -> list[SchemaRootConditional]:
    """Collect cross-section conditionals from a single group."""
    results: list[SchemaRootConditional] = []
    if not group.fields or not group.fields.conditional:
        return results
    for name, entry in group.fields.conditional.items():
        active = entry.only_when or entry.always_when or entry.not_when
        if active is None or not active.field.startswith("."):
            continue
        mode = "only_when" if entry.only_when else ("always_when" if entry.always_when else "not_when")
        results.append(build_root_conditional(active, name, group_path, mode))
    return results


