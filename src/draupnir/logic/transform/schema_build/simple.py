"""Schema building — branching builders.

CC=2-3 builders. Each has a small number of branches or a single
iteration. Looks up pre-built children from the build context using
cache key strings extracted from generated input model RootModel wrappers.
"""

from pydantic import BaseModel, RootModel

from draupnir.structure.config.build_context import BuildContext
from draupnir.structure.model.schema_output import (
    FieldMeta,
    SchemaArray,
    SchemaField,
    SchemaOneOf,
    SchemaOneOfField,
    SchemaRef,
    SchemaTupleArray,
)


def optional_tuple[T](items: list[T]) -> tuple[T, ...] | None:
    """Return tuple of items if non-empty, else None."""
    return tuple(items) if items else None


def build_items_or_one_of(
    items_wrapper: RootModel,
    context: BuildContext,
) -> BaseModel | SchemaOneOf:
    """Build items schema: single ref or oneOf from a typed container.

    items_wrapper.root is either a RootModel[str] (single ref) or a
    *OneOf model with .oneOf.root -> list of RootModel[str] members.
    """
    inner = items_wrapper.root
    if isinstance(inner, RootModel):
        return context.built[inner.root]
    members = tuple(context.built[member.root] for member in inner.oneOf.root)
    return SchemaOneOf(one_of=members)


def build_element(model: BaseModel, context: BuildContext) -> SchemaField:
    """Element -> inherits atom/enum schema, adds format."""
    base = context.full[model.inherits.root]
    format_value = model.format.root if model.format else None
    return SchemaField(
        title=model.title.root,
        type=base.type,
        pattern=base.pattern,
        enum=base.enum,
        not_=base.not_ if isinstance(base, SchemaField) else None,
        format=format_value,
        description=model.description.root,
    )


def build_union(model: BaseModel, context: BuildContext) -> SchemaOneOfField:
    """Union -> {oneOf: [member schemas or $refs]}."""
    members = tuple(context.built[member.root] for member in model.union.root)
    return SchemaOneOfField(
        title=model.title.root,
        one_of=members,
        description=model.description.root,
    )


def build_array(model: BaseModel, context: BuildContext) -> SchemaArray:
    """Array -> {type: array, items: object_or_oneOf}."""
    items = build_items_or_one_of(model.items, context)
    return SchemaArray(
        title=model.title.root,
        items=items,
        description=model.description.root,
        min_items=1,
    )


def build_superarray(model: BaseModel, context: BuildContext) -> SchemaArray:
    """Superarray -> {type: array, items: object_or_oneOf}."""
    items = build_items_or_one_of(model.items, context)
    return SchemaArray(
        title=model.title.root,
        items=items,
        description=model.description.root,
        min_items=1,
    )


def build_field_ref(
    ref_string: str,
    field_model: BaseModel,
    meta: FieldMeta,
) -> SchemaRef:
    """Build a SchemaRef with field-level metadata annotations.

    Used when the inner type is shared ($defs) — metadata attaches
    as sibling keywords alongside $ref.
    """
    default_value = field_model.default.root if field_model.default else None
    const_value = field_model.const.root if field_model.const else None
    return SchemaRef(
        ref=ref_string, title=field_model.title.root, description=meta.description,
        default=default_value, const=const_value, min_length=meta.min_length,
        x_semantic=meta.semantic, x_constraint=meta.constraint,
    )


def build_tuple(model: BaseModel, context: BuildContext) -> SchemaTupleArray:
    """Tuple -> {prefixItems, items: false}."""
    prefix = tuple(context.built[item.root] for item in model.items.root)
    return SchemaTupleArray(
        title=model.title.root,
        prefix_items=prefix,
        description=model.description.root,
        min_items=len(prefix),
        max_items=len(prefix),
    )
