"""Field-level and simple container builders.

Converts Verdandi field models (Pattern, Atom, Enum, Element, Union)
and simple containers (Tuple, Simplearray, Simplegroup) into JSON Schema
output models. These builders are $defs-unaware — they produce inline
schemas. Callers route through build_or_ref() for $defs extraction.

No IO. Pure model-to-model conversion.
"""

from pydantic import BaseModel

from draupnir.structures.conditionals import ConditionalWhen
from draupnir.structures.fields import (
    Atom,
    Element,
)
from draupnir.structures.fields import Enum as VerdandiEnum
from draupnir.structures.fields import (
    Pattern,
    Union_,
)
from draupnir.structures.schema_output import (
    SchemaAnyOfConstraint,
    SchemaArray,
    SchemaCondition,
    SchemaConditional,
    SchemaConst,
    SchemaEnumConstraint,
    SchemaField,
    SchemaObject,
    SchemaOneOfField,
    SchemaPatternConstraint,
    SchemaTupleArray,
)
from draupnir.structures.simple_containers import (
    Simplearray,
    Simplegroup,
    Tuple_,
)


def build_excludes(
    excludes: tuple[Pattern, ...],
) -> SchemaPatternConstraint | SchemaAnyOfConstraint:
    """Convert Verdandi excludes patterns to JSON Schema not constraint."""
    if len(excludes) == 1:
        return SchemaPatternConstraint(pattern=excludes[0].regex)
    return SchemaAnyOfConstraint(
        any_of=tuple(SchemaPatternConstraint(pattern=p.regex) for p in excludes),
    )


def build_atom(atom: Atom) -> SchemaField:
    """Atom -> {type, pattern?, not?, description}."""
    pattern = atom.pattern.regex if atom.pattern else None
    not_constraint = build_excludes(atom.excludes) if atom.excludes else None
    return SchemaField(
        type=atom.type,
        pattern=pattern,
        not_=not_constraint,
        description=atom.description,
    )


def build_enum(enum_model: VerdandiEnum) -> SchemaField:
    """Enum -> {type: string, enum: [...]}."""
    return SchemaField(
        type="string",
        enum=enum_model.values,
        description=enum_model.description,
    )


def build_element(element: Element) -> SchemaField:
    """Element -> inherits atom/enum schema, adds format."""
    base = build_field(element.inherits)
    return SchemaField(
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
    return SchemaOneOfField(one_of=members, description=union_model.description)


def build_field(model: Pattern | Atom | VerdandiEnum | Element | Union_) -> SchemaField | SchemaOneOfField:
    """Dispatch field model to its builder."""
    if isinstance(model, Pattern):
        return SchemaField(type="string", pattern=model.regex, description=model.description)
    if isinstance(model, Atom):
        return build_atom(model)
    if isinstance(model, VerdandiEnum):
        return build_enum(model)
    if isinstance(model, Element):
        return build_element(model)
    if isinstance(model, Union_):
        return build_union(model)
    msg = f"unexpected field model: {type(model).__name__}"
    raise TypeError(msg)


def build_tuple(tuple_model: Tuple_) -> SchemaTupleArray:
    """Tuple -> {prefixItems: [...], items: false}."""
    prefix = tuple(build_field(item) for item in tuple_model.items)
    return SchemaTupleArray(
        prefix_items=prefix,
        description=tuple_model.description,
        min_items=len(prefix),
        max_items=len(prefix),
    )


def build_simplearray(simplearray: Simplearray) -> SchemaArray:
    """Simplearray -> {type: array, items: {field}}."""
    return SchemaArray(
        items=build_field(simplearray.items),
        description=simplearray.description,
    )


def build_simple(model: BaseModel) -> SchemaField | SchemaOneOfField | SchemaTupleArray | SchemaArray:
    """Dispatch field or simple container to its builder."""
    if isinstance(model, Tuple_):
        return build_tuple(model)
    if isinstance(model, Simplearray):
        return build_simplearray(model)
    return build_field(model)


def build_simplegroup(simplegroup: Simplegroup) -> SchemaObject:
    """Simplegroup -> {type: object, properties, required}."""
    properties: dict[str, SchemaField | SchemaOneOfField | SchemaTupleArray | SchemaArray] = {}
    required_keys: list[str] = []

    for zone, is_required in ((simplegroup.required, True), (simplegroup.optional, False)):
        if zone:
            for name, ref in zone.items():
                properties[name] = build_simple(ref)
                if is_required:
                    required_keys.append(name)

    conditionals: list[SchemaConditional] = []
    if simplegroup.conditional:
        for name, entry in simplegroup.conditional.items():
            properties[name] = build_simple(entry.ref)
            conditionals.append(
                build_conditional_entry(name, entry.only_when, entry.always_when, entry.not_when),
            )

    return SchemaObject(
        properties=properties,
        required=tuple(required_keys) if required_keys else None,
        additional_properties=False,
        all_of=tuple(conditionals) if conditionals else None,
        description=simplegroup.description,
    )


def build_if_condition(when: ConditionalWhen) -> SchemaCondition:
    """Build the if-clause from a ConditionalWhen."""
    if when.equals is not None:
        constraint: SchemaConst | SchemaEnumConstraint = SchemaConst(const=when.equals)
    else:
        constraint = SchemaEnumConstraint(enum=when.in_)
    return SchemaCondition(properties={when.field: constraint})


def build_conditional_entry(
    field_name: str,
    only_when: ConditionalWhen | None,
    always_when: ConditionalWhen | None,
    not_when: ConditionalWhen | None,
) -> SchemaConditional:
    """Build if/then/else from conditional when values.

    only_when: required when true, forbidden when false.
    always_when: required when true, no effect when false.
    not_when: forbidden when true, no effect when false.
    """
    if only_when:
        return SchemaConditional(
            if_=build_if_condition(only_when),
            then_=SchemaCondition(required=(field_name,)),
            else_=SchemaCondition(properties={field_name: False}),
        )
    if always_when:
        return SchemaConditional(
            if_=build_if_condition(always_when),
            then_=SchemaCondition(required=(field_name,)),
        )
    if not_when:
        return SchemaConditional(
            if_=build_if_condition(not_when),
            then_=SchemaCondition(properties={field_name: False}),
        )
    msg = "exactly one of only_when/always_when/not_when must be set"
    raise ValueError(msg)
