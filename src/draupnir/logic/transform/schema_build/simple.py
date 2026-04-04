"""Schema building — branching builders.

CC=2-3 builders. Each resolves child schemas from BuildContext by
extracting cache key strings through generated input model RootModel
wrappers (.root access). The build context is populated bottom-up by
the compile loop (orchestrate), so all children are guaranteed to exist
by the time their parent builder runs.

The two context dicts serve different purposes:
- context.built: may contain SchemaRef if the node was promoted to $defs
- context.full: always contains the complete schema, used when the caller
  needs actual field values (e.g., element inheriting atom's pattern)
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
    """Convert list to tuple, or None if empty.

    JSON Schema uses null (absent key) rather than empty arrays for
    optional array fields like "required". Pydantic's exclude_none
    serialization then omits these cleanly.
    """
    return tuple(items) if items else None


def build_items_or_one_of(
    items_wrapper: RootModel,
    context: BuildContext,
) -> BaseModel | SchemaOneOf:
    """Build items schema: single ref or oneOf from a typed container.

    Dispatches on the inner type after unwrapping the outer RootModel:
    - RootModel[str]: single type ref → look up built schema directly
    - *OneOf model: has .oneOf.root → list of RootModel[str] members,
      each resolved and wrapped in SchemaOneOf

    This handles the Verdandi pattern where array items can be either a
    single type or a union of types (oneOf).
    """
    inner = items_wrapper.root
    if isinstance(inner, RootModel):
        return context.built[inner.root]
    members = tuple(context.built[member.root] for member in inner.oneOf.root)
    return SchemaOneOf(one_of=members)


def build_element(model: BaseModel, context: BuildContext) -> SchemaField:
    """Element -> inherits atom/enum schema, adds format.

    Uses context.full (not .built) because the inherited type may have
    been promoted to $defs — but element needs the actual type/pattern/enum
    values from the full schema to copy into its own SchemaField.
    """
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


def build_field_ref(
    ref_string: str,
    field_model: BaseModel,
    meta: FieldMeta,
) -> SchemaRef:
    """Build a SchemaRef with field-level metadata annotations.

    When a field's inner type was promoted to $defs, context.built holds
    a SchemaRef instead of the inline schema. Field metadata (title,
    description, default, const, min_length, semantic, constraint) must
    be carried as sibling keywords alongside $ref — JSON Schema allows
    this and validators merge them at evaluation time.
    """
    default_value = field_model.default.root if field_model.default else None
    const_value = field_model.const.root if field_model.const else None
    return SchemaRef(
        ref=ref_string, title=field_model.title.root, description=meta.description,
        default=default_value, const=const_value,
        min_length=meta.min_length, max_length=meta.max_length,
        x_semantic=meta.semantic, x_constraint=meta.constraint,
    )


def build_tuple(model: BaseModel, context: BuildContext) -> SchemaTupleArray:
    """Tuple -> fixed-length array with prefixItems (JSON Schema 2020-12).

    items=false (set on SchemaTupleArray) forbids additional items beyond
    the prefix. min_items=max_items=len(prefix) enforces exact length.
    """
    prefix = tuple(context.built[item.root] for item in model.items.root)
    return SchemaTupleArray(
        title=model.title.root,
        prefix_items=prefix,
        description=model.description.root,
        min_items=len(prefix),
        max_items=len(prefix),
    )
