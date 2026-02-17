"""Stage composition: schema YAML → SchemaDocument.

IMPURE: Calls loaders (IO) and composes pure stages.
This is the thin orchestrator — no logic, just wiring.
"""

from pathlib import Path, PurePosixPath

from draupnir.functions.impure.loaders import (
    load_all_primitives,
    load_blocklist_composed,
    load_composed_type_adopters,
    load_schema,
    make_schema_loaders,
)
from draupnir.functions.pure.builders import build_schema_document
from draupnir.functions.pure.resolvers import (
    build_blocklists,
    build_primitives_pool,
    build_schema_sections_dict,
    resolve_walked_schema,
)
from draupnir.functions.pure.walkers import walk_schema
from draupnir.structures import RawSchema, SchemaDocument


def generate_schema(
    schema_path: Path,
    toolcompose_root: Path,
) -> SchemaDocument:
    """Full pipeline: schema YAML → SchemaDocument (typed, not dict).

    Stages:
    1. Load primitives pool (IO)
    2. Load schema root (IO)
    3. Bridge sections dict (pure)
    4. Walk tree (pure with injected IO)
    5. Resolve type adoption (pure)
    6. Build JSON Schema output models (pure)
    """
    primitives = load_all_primitives(toolcompose_root / "primitives")
    adopters = load_composed_type_adopters(toolcompose_root / "composed")
    pool = build_primitives_pool(primitives + adopters)

    blocklist_composed = load_blocklist_composed(toolcompose_root / "composed")
    blocklists = build_blocklists(blocklist_composed, pool)

    raw_schema = load_schema(schema_path)
    raw_schema = bridge_schema_sections(raw_schema)

    loaders = make_schema_loaders(toolcompose_root)
    walked = walk_schema(raw_schema, PurePosixPath(""), loaders)

    resolved = resolve_walked_schema(walked, pool, blocklists)
    return build_schema_document(resolved)


def bridge_schema_sections(schema: RawSchema) -> RawSchema:
    """Ensure schema has a populated sections dict.

    Current schema YAMLs list sections by name only. This bridges
    to the walker's expected format until Phase 5 adds explicit paths.
    Returns the schema unchanged if sections dict already exists.
    """
    sections_dict = build_schema_sections_dict(schema)
    if sections_dict == dict(schema.sections or {}):
        return schema
    return RawSchema(
        name=schema.name,
        version=schema.version,
        description=schema.description,
        additional_properties=schema.additional_properties,
        sections=sections_dict,
        required_sections=schema.required_sections,
        optional_sections=schema.optional_sections,
    )


def discover_schema_paths(schema_dir: Path) -> list[Path]:
    """Find all schema YAML files in a directory."""
    if not schema_dir.exists():
        return []
    return sorted(schema_dir.glob("*.yaml"))


def generate_all_schemas(
    toolcompose_root: Path,
) -> dict[str, SchemaDocument]:
    """Generate all schemas found in toolcompose_root/schema/.

    Returns dict mapping schema name to SchemaDocument.
    """
    schema_dir = toolcompose_root / "schema"
    results: dict[str, SchemaDocument] = {}
    for schema_path in discover_schema_paths(schema_dir):
        doc = generate_schema(schema_path, toolcompose_root)
        results[doc.title] = doc
    return results
