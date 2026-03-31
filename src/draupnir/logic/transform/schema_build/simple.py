"""Schema building — branching builders.

CC=2-3 builders. Each has a small number of branches or a single
iteration. Recursive descent is injected via build_fn (DI).
"""

from collections.abc import Callable

from pydantic import BaseModel

from draupnir.structure.model.complex_containers import (
    Array,
    ArrayOneOf,
    Superarray,
    SuperarrayOneOf,
)
from draupnir.structure.model.fields import Atom, Element, Pattern, Union_
from draupnir.structure.model.schema_output import (
    SchemaAnyOfConstraint,
    SchemaArray,
    SchemaField,
    SchemaOneOf,
    SchemaOneOfField,
    SchemaPatternConstraint,
    SchemaTupleArray,
)


def optional_tuple[T](items: list[T]) -> tuple[T, ...] | None:
    """Return tuple of items if non-empty, else None."""
    return tuple(items) if items else None


def build_items_or_one_of(
    items: BaseModel,
    one_of_type: type,
    build_fn: Callable[[BaseModel], BaseModel],
) -> BaseModel | SchemaOneOf:
    """Build items schema: single item or oneOf from a typed container."""
    if isinstance(items, one_of_type):
        return SchemaOneOf(one_of=tuple(build_fn(member) for member in items.one_of))
    return build_fn(items)


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


def build_element(
    element: Element,
    build_fn: Callable[[BaseModel], BaseModel],
) -> SchemaField:
    """Element -> inherits atom/enum schema, adds format."""
    base = build_fn(element.inherits)
    return SchemaField(
        title=element.title,
        type=base.type,
        pattern=base.pattern,
        enum=base.enum,
        not_=base.not_ if isinstance(base, SchemaField) else None,
        format=element.format,
        description=element.description,
    )


def build_union(
    union_model: Union_,
    build_fn: Callable[[BaseModel], BaseModel],
) -> SchemaOneOfField:
    """Union -> {oneOf: [member schemas or $refs]}."""
    members = tuple(build_fn(member) for member in union_model.union)
    return SchemaOneOfField(
        title=union_model.title, one_of=members, description=union_model.description,
    )


def build_array(
    array: Array,
    build_fn: Callable[[BaseModel], BaseModel],
) -> SchemaArray:
    """Array -> {type: array, items: object_or_oneOf}."""
    items = build_items_or_one_of(array.items, ArrayOneOf, build_fn)
    return SchemaArray(
        title=array.title, items=items,
        description=array.description, min_items=1,
    )


def build_superarray(
    superarray: Superarray,
    build_fn: Callable[[BaseModel], BaseModel],
) -> SchemaArray:
    """Superarray -> {type: array, items: object_or_oneOf}."""
    items = build_items_or_one_of(superarray.items, SuperarrayOneOf, build_fn)
    return SchemaArray(
        title=superarray.title, items=items,
        description=superarray.description, min_items=1,
    )


def build_tuple(
    tuple_model: BaseModel,
    build_fn: Callable[[BaseModel], BaseModel],
) -> SchemaTupleArray:
    """Tuple -> {prefixItems, items: false}."""
    prefix = tuple(build_fn(item) for item in tuple_model.items)
    return SchemaTupleArray(
        title=tuple_model.title,
        prefix_items=prefix,
        description=tuple_model.description,
        min_items=len(prefix),
        max_items=len(prefix),
    )
