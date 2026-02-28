"""Schema export — assemble SchemaDocuments from loaded models.

Walks the model tree to identify shared nodes for $defs, then builds
SchemaDocument output using the container builders. Generic tree walk
uses Pydantic model field iteration — no per-type walk code.

No IO. Pure computation on frozen models.
"""

from collections.abc import Iterator

from pydantic import BaseModel

from draupnir.functions.pure.build_containers import build_model, build_or_ref
from draupnir.functions.pure.build_cross_section import collect_schema_conditionals
from draupnir.structures.schema_output import (
    SchemaArray,
    SchemaDocument,
    SchemaNullableObject,
    SchemaNullType,
    SchemaObject,
)
from draupnir.structures.top_level import Schema


def reverse_cache_index(cache: dict[str, BaseModel]) -> dict[int, str]:
    """Build id(model) -> cache_key mapping for $defs lookup."""
    return {id(model): key for key, model in cache.items()}


def iter_child_models(model: BaseModel) -> Iterator[BaseModel]:
    """Yield all direct BaseModel children from a model's fields."""
    for field_name in type(model).model_fields:
        value = getattr(model, field_name)
        if isinstance(value, BaseModel):
            yield value
        elif isinstance(value, dict):
            yield from (item for item in value.values() if isinstance(item, BaseModel))
        elif isinstance(value, tuple):
            yield from (item for item in value if isinstance(item, BaseModel))


def count_refs(
    root: BaseModel,
    reverse: dict[int, str],
) -> dict[str, int]:
    """Count cache key occurrences in model tree for $defs detection.

    Iterative walk. Each unique model is visited once, but its cache
    key is counted every time it appears as a child. Keys with count
    >= 2 are shared nodes — candidates for $defs extraction.
    """
    counts: dict[str, int] = {}
    visited: set[int] = set()
    stack = [root]
    while stack:
        model = stack.pop()
        if id(model) in visited:
            continue
        visited.add(id(model))
        for child in iter_child_models(model):
            cache_key = reverse.get(id(child))
            if cache_key:
                counts[cache_key] = counts.get(cache_key, 0) + 1
            stack.append(child)
    return counts


def shared_keys(counts: dict[str, int]) -> frozenset[str]:
    """Return cache keys appearing 2+ times (candidates for $defs)."""
    return frozenset(key for key, count in counts.items() if count >= 2)


def build_schema_properties(
    schema: Schema,
    reverse: dict[int, str],
    shared: frozenset[str],
    defs: dict[str, BaseModel],
) -> dict[str, BaseModel]:
    """Build top-level properties dict from schema sections."""
    properties: dict[str, BaseModel] = {}
    nullable_set = frozenset(schema.nullable) if schema.nullable else frozenset()
    all_sections: dict[str, BaseModel] = {}
    if schema.shallowsections:
        all_sections.update(schema.shallowsections)
    if schema.sections:
        all_sections.update(schema.sections)
    for name, section in all_sections.items():
        built = build_or_ref(section, reverse, shared, defs)
        if name in nullable_set and isinstance(built, SchemaObject):
            properties[name] = SchemaNullableObject(
                one_of=(built, SchemaNullType()),
                description=built.description,
            )
        else:
            properties[name] = built
    return properties


def export_schema(
    schema: Schema,
    schema_key: str,
    cache: dict[str, BaseModel],
) -> SchemaDocument:
    """Build a complete SchemaDocument from a loaded Schema model."""
    reverse = reverse_cache_index(cache)
    counts = count_refs(schema, reverse)
    shared = shared_keys(counts)
    defs: dict[str, BaseModel] = {}
    properties = build_schema_properties(schema, reverse, shared, defs)
    cross_section = collect_schema_conditionals(schema)
    schema_name = schema_key.split("/", 1)[1]
    return SchemaDocument(
        schema_uri="https://json-schema.org/draft/2020-12/schema",
        schema_id=f"{schema_name}.schema.json",
        title=schema.title,
        description=schema.description,
        required=schema.required,
        properties=properties,
        additional_properties=False,
        defs=defs if defs else None,
        all_of=cross_section,
    )


def wrap_array_as_object(array: SchemaArray) -> SchemaObject:
    """Wrap a SchemaArray in a SchemaObject with an 'items' property.

    TOML root is always a table — bare arrays can't be represented.
    Include files use 'items' as the key for their array content.
    """
    return SchemaObject(
        title=array.title,
        description=array.description,
        properties={"items": array},
        required=("items",),
        additional_properties=False,
    )


def export_fragment(
    model: BaseModel,
    cache: dict[str, BaseModel],
) -> tuple[BaseModel, dict[str, BaseModel]]:
    """Build a standalone schema fragment from any Verdandi model.

    Array fragments are wrapped in an object with an 'items' property
    so they can validate TOML include files (TOML root is always a table).
    Returns the built schema model and any accumulated $defs.
    """
    reverse = reverse_cache_index(cache)
    counts = count_refs(model, reverse)
    shared = shared_keys(counts)
    defs: dict[str, BaseModel] = {}
    built = build_model(model, reverse, shared, defs)
    if isinstance(built, SchemaArray):
        built = wrap_array_as_object(built)
    return built, defs


def export_all_schemas(
    cache: dict[str, BaseModel],
) -> dict[str, SchemaDocument]:
    """Export all schemas from a populated cache."""
    results: dict[str, SchemaDocument] = {}
    for key, model in cache.items():
        if isinstance(model, Schema):
            results[key] = export_schema(model, key, cache)
    return results
