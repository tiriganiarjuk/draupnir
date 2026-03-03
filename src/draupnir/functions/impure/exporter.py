"""Schema export — assemble SchemaDocuments from loaded models.

Builds SchemaDocument output by calling the dispatch layer (which
mutates the $defs accumulator). Uses pure tree_walk functions for
shared node detection.
"""

from pydantic import BaseModel

from draupnir.functions.impure.dispatch import build_model, build_or_ref
from draupnir.functions.pure.build_cross_section import collect_schema_conditionals
from draupnir.functions.pure.tree_walk import (
    count_refs,
    reverse_cache_index,
    shared_keys,
    wrap_array_as_object,
)
from draupnir.structures.schema_output import (
    SchemaArray,
    SchemaDocument,
    SchemaNullableObject,
    SchemaNullType,
    SchemaObject,
)
from draupnir.structures.top_level import Schema


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


def export_fragment(
    model: BaseModel,
    cache: dict[str, BaseModel],
) -> tuple[SchemaObject, dict[str, BaseModel]]:
    """Build a standalone schema fragment from any Verdandi model.

    Array fragments are wrapped in an object with an 'items' property
    so they can validate TOML include files (TOML root is always a table).
    Returns the built SchemaObject and any accumulated $defs.
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
