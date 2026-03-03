"""Leaf field converters for Verdandi type models.

Converts Pattern, Atom, Enum, Element, Union into JSON Schema output
models. These are leaf converters — they produce inline schemas without
$defs awareness. Callers route through dispatch.build_or_ref() for
$defs extraction.

No IO. Pure model-to-model conversion.
"""

from draupnir.structures.fields import Atom, Element, Pattern, Union_
from draupnir.structures.fields import Enum as VerdandiEnum
from draupnir.structures.schema_output import (
    SchemaAnyOfConstraint,
    SchemaField,
    SchemaOneOfField,
    SchemaPatternConstraint,
)


def build_excludes(
    excludes: tuple[Pattern, ...],
) -> SchemaPatternConstraint | SchemaAnyOfConstraint:
    """Convert Verdandi excludes patterns to JSON Schema not constraint."""
    if len(excludes) == 1:
        return SchemaPatternConstraint(pattern=excludes[0].regex)
    return SchemaAnyOfConstraint(
        any_of=tuple(SchemaPatternConstraint(pattern=excl.regex) for excl in excludes),
    )


def build_atom(atom: Atom) -> SchemaField:
    """Atom -> {type, pattern?, minLength?, not?, description}."""
    pattern = atom.pattern.regex if atom.pattern else None
    not_constraint = build_excludes(atom.excludes) if atom.excludes else None
    return SchemaField(
        title=atom.title,
        type=atom.type,
        pattern=pattern,
        min_length=atom.min_length,
        not_=not_constraint,
        description=atom.description,
    )


def build_enum(enum_model: VerdandiEnum) -> SchemaField:
    """Enum -> {type: string, enum: [...]}."""
    return SchemaField(
        title=enum_model.title,
        type="string",
        enum=enum_model.values,
        description=enum_model.description,
    )


def build_element(element: Element) -> SchemaField:
    """Element -> inherits atom/enum schema, adds format."""
    base = build_field(element.inherits)
    return SchemaField(
        title=element.title,
        type=base.type,
        pattern=base.pattern,
        enum=base.enum,
        not_=base.not_ if isinstance(base, SchemaField) else None,
        format=element.format,
        description=element.description,
    )


def build_union(union_model: Union_) -> SchemaOneOfField:
    """Union -> {oneOf: [member schemas]}."""
    members = tuple(build_field(member) for member in union_model.union)
    return SchemaOneOfField(
        title=union_model.title, one_of=members, description=union_model.description,
    )


def build_field(
    model: Pattern | Atom | VerdandiEnum | Element | Union_,
) -> SchemaField | SchemaOneOfField:
    """Dispatch field model to its builder."""
    if isinstance(model, Pattern):
        return SchemaField(
            title=model.title, type="string",
            pattern=model.regex, description=model.description,
        )
    if isinstance(model, Atom):
        return build_atom(model)
    if isinstance(model, VerdandiEnum):
        return build_enum(model)
    if isinstance(model, Element):
        return build_element(model)
    return build_union(model)
