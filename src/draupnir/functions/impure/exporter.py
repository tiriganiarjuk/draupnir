"""Schema export — assemble SchemaDocuments from loaded models.

Builds SchemaDocument output by calling the dispatch layer (which
mutates the $defs accumulator). Uses pure tree_walk functions for
shared node detection.
"""

from pydantic import BaseModel

from draupnir.functions.impure.dispatch import build_model, build_or_ref
from draupnir.functions.pure.build_cross_section import build_root_conditional
from draupnir.functions.pure.collect_cross_section import collect_schema_conditionals
from draupnir.functions.pure.converters.conditional import is_cross_section
from draupnir.functions.pure.tree_walk import (
    count_refs,
    reverse_cache_index,
    shared_keys,
    wrap_array_as_object,
)
from draupnir.structures.schema_output import (
    SchemaArray,
    SchemaDocument,
    SchemaRootConditional,
)
from draupnir.structures.top_level import (
    Schema,
    SchemaSections,
    SchemaShallowsections,
)


def build_schema_properties(
    zones: SchemaSections | SchemaShallowsections,
    reverse: dict[int, str],
    shared: frozenset[str],
    defs: dict[str, BaseModel],
) -> tuple[dict[str, BaseModel], list[str]]:
    """Build top-level properties and required keys from schema zones."""
    properties: dict[str, BaseModel] = {}
    required_keys: list[str] = []
    if zones.required:
        for name, ref in zones.required.items():
            properties[name] = build_or_ref(ref, reverse, shared, defs)
            required_keys.append(name)
    if zones.optional:
        for name, ref in zones.optional.items():
            properties[name] = build_or_ref(ref, reverse, shared, defs)
    if zones.conditional:
        for name, entry in zones.conditional.items():
            properties[name] = build_or_ref(entry.ref, reverse, shared, defs)
    return properties, required_keys


def collect_schema_zone_conditionals(
    zones: SchemaSections | SchemaShallowsections,
) -> list[SchemaRootConditional]:
    """Build root conditionals from the schema conditional zone.

    All schema-level conditionals produce SchemaRootConditional entries
    for the document allOf. Both same-object presence checks and
    cross-section traversals route through build_root_conditional.
    """
    results: list[SchemaRootConditional] = []
    if not zones.conditional:
        return results
    for name, entry in zones.conditional.items():
        active = entry.only_when or entry.always_when or entry.not_when
        if active is None:
            continue
        mode = (
            "only_when" if entry.only_when
            else ("always_when" if entry.always_when else "not_when")
        )
        if is_cross_section(active):
            target_path = ()
        else:
            target_path = ()
        results.append(build_root_conditional(active, name, target_path, mode))
    return results


def merge_all_conditionals(
    schema: Schema,
    zones: SchemaSections | SchemaShallowsections,
) -> tuple[SchemaRootConditional, ...] | None:
    """Merge schema zone conditionals with cross-section conditionals."""
    results: list[SchemaRootConditional] = []
    results.extend(collect_schema_zone_conditionals(zones))
    cross_section = collect_schema_conditionals(schema)
    if cross_section:
        results.extend(cross_section)
    return tuple(results) if results else None


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
    zones = schema.sections or schema.shallowsections
    properties, required_keys = build_schema_properties(
        zones, reverse, shared, defs,
    )
    schema_name = schema_key.split("/", 1)[1]
    return SchemaDocument(
        schema_uri="https://json-schema.org/draft/2020-12/schema",
        schema_id=f"{schema_name}.schema.json",
        title=schema.title,
        description=schema.description,
        required=tuple(required_keys) if required_keys else None,
        properties=properties,
        additional_properties=False,
        defs=defs if defs else None,
        all_of=merge_all_conditionals(schema, zones),
    )


def export_fragment(
    model: BaseModel,
    cache: dict[str, BaseModel],
) -> tuple[BaseModel, dict[str, BaseModel]]:
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
