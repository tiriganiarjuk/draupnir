"""Schema pipeline orchestration — wire all zones together.

Orchestrate level (CC=1-5). Chains dispatch table, composed builders,
tree_walk analysis, and export assembly. This is the single orchestrate
module — all cross-zone wiring lives here.
"""

import sys
from collections.abc import Callable
from functools import partial
from pathlib import Path

from pydantic import BaseModel

from draupnir.logic.impure.dispatch.primitive import cache_key_to_defs_key
from draupnir.logic.impure.loader.primitive import extract_cache_name
from draupnir.logic.impure.loader.assembled import load_all_levels
from draupnir.logic.impure.pipeline.composed import resolve_paths
from draupnir.logic.impure.pipeline.primitive import fragment_output_name, schema_filename
from draupnir.logic.impure.pipeline.simple import args_to_paths, context_to_paths, find_workspace_root
from draupnir.logic.impure.writer.primitive import serialize_schema
from draupnir.logic.impure.writer.simple import write_schema
from draupnir.logic.pure.tree_walk.composed import count_refs
from draupnir.logic.pure.tree_walk.primitive import wrap_array_as_object
from draupnir.logic.pure.tree_walk.simple import reverse_cache_index, shared_keys
from draupnir.logic.orchestrate.compile.dispatch import dispatch
from draupnir.logic.transform.conditional_build.composed import (
    collect_schema_zone_conditionals,
    collect_section_conditionals,
    iter_schema_sections,
)
from draupnir.logic.transform.field_annotate.assembled import build_verdandi_field_refs
from draupnir.logic.transform.ref_resolve.composed import resolve_refs
from draupnir.logic.transform.schema_build.assembled import (
    build_group,
    build_section,
    build_shallowsection,
    build_simplegroup,
)
from draupnir.logic.transform.schema_build.composed import build_field, build_schema_properties
from draupnir.structure.config.fragments import Fragment
from draupnir.structure.config.pipeline import PipelineArgs, PipelineContext, PipelineMode
from draupnir.structure.model.complex_containers import Group
from draupnir.structure.model.schema_output import (
    FragmentDocument,
    SchemaArray,
    SchemaDocument,
    SchemaRef,
    SchemaRootConditional,
)
from draupnir.structure.model.simple_containers import Simplegroup, VerdandiField
from draupnir.structure.model.top_level import (
    Schema,
    SchemaSections,
    SchemaShallowsections,
    Section,
    Shallowsection,
)


# --- Schema building ---


def build_or_ref(
    model: BaseModel,
    reverse: dict[int, str],
    shared: frozenset[str],
    defs: dict[str, BaseModel],
    build_model_fn: Callable[..., BaseModel],
) -> BaseModel:
    """Build schema for a model, or return $ref if shared."""
    cache_key = reverse.get(id(model))
    if cache_key and cache_key in shared:
        def_name = cache_key_to_defs_key(cache_key)
        if def_name not in defs:
            defs[def_name] = build_model_fn(model, reverse, shared, defs)
        return SchemaRef(ref=f"#/$defs/{def_name}")
    return build_model_fn(model, reverse, shared, defs)


def resolve_container_handler(
    model: BaseModel,
) -> Callable | None:
    """Look up builder for composed container types."""
    if isinstance(model, Simplegroup):
        return build_simplegroup
    if isinstance(model, Group):
        return build_group
    if isinstance(model, Section):
        return build_section
    if isinstance(model, Shallowsection):
        return build_shallowsection
    return None


def resolve_handler(
    model: BaseModel,
) -> Callable | None:
    """Look up builder for a model type across all levels."""
    handler = dispatch.get(type(model))
    if handler:
        return handler
    if isinstance(model, VerdandiField):
        return build_verdandi_field_refs
    return resolve_container_handler(model)


def build_model(
    model: BaseModel,
    reverse: dict[int, str],
    shared: frozenset[str],
    defs: dict[str, BaseModel],
) -> BaseModel:
    """Dispatch any Verdandi model to its type-specific converter."""
    build_fn = partial(
        build_or_ref, reverse=reverse, shared=shared, defs=defs,
        build_model_fn=build_model,
    )
    handler = resolve_handler(model)
    if handler:
        return handler(model, build_fn)
    return build_field(model)


# --- Conditional assembly (CC=3, orchestrate) ---


def collect_schema_conditionals(
    schema: Schema,
) -> tuple[SchemaRootConditional, ...] | None:
    """Collect all cross-section conditionals from a Schema."""
    results: list[SchemaRootConditional] = []
    for name, section in iter_schema_sections(schema).items():
        results.extend(collect_section_conditionals(section, name))
    if not results:
        return None
    return tuple(results)


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


# --- Schema export ---


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
    build_fn = partial(
        build_or_ref, reverse=reverse, shared=shared, defs=defs,
        build_model_fn=build_model,
    )
    zones = schema.sections or schema.shallowsections
    properties, required_keys = build_schema_properties(zones, build_fn)
    schema_name = extract_cache_name(schema_key)
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
    """Build a standalone schema fragment from any Verdandi model."""
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
    for cache_key, model in cache.items():
        if isinstance(model, Schema):
            results[cache_key] = export_schema(model, cache_key, cache)
    return results


# --- Pipeline modes ---


def run_all(
    verdandi_root: Path,
    output_dir: Path,
) -> int:
    """Load everything, export all schemas, write all files."""
    cache: dict[str, BaseModel] = {}
    load_all_levels(verdandi_root, cache, resolve_refs)
    if not cache:
        sys.stderr.write("error: no files loaded — nothing to generate\n")
        return 1
    schemas = export_all_schemas(cache)
    if not schemas:
        sys.stderr.write("error: no schemas exported from loaded cache\n")
        return 1
    for schema_key, document in schemas.items():
        output_path = output_dir / schema_filename(schema_key)
        write_schema(document, output_path)
        sys.stdout.write(f"wrote {output_path.name}\n")
    return 0


def run_check(
    verdandi_root: Path,
    output_dir: Path,
) -> int:
    """Check for drift without writing. Exit 1 if any schema drifted."""
    cache: dict[str, BaseModel] = {}
    load_all_levels(verdandi_root, cache, resolve_refs)
    schemas = export_all_schemas(cache)
    drift = False
    for schema_key, document in schemas.items():
        output_path = output_dir / schema_filename(schema_key)
        generated = serialize_schema(document) + "\n"
        if not output_path.exists() or output_path.read_text() != generated:
            sys.stderr.write(f"DRIFT   {output_path.name}\n")
            drift = True
        else:
            sys.stdout.write(f"OK      {output_path.name}\n")
    return 1 if drift else 0


def run_fragments(
    verdandi_root: Path,
    output_dir: Path,
) -> int:
    """Export standalone include-fragment schemas."""
    cache: dict[str, BaseModel] = {}
    load_all_levels(verdandi_root, cache, resolve_refs)
    for fragment in Fragment:
        model = cache.get(fragment.value)
        if model is None:
            sys.stderr.write(f"ERROR: {fragment.value} not in cache\n")
            return 1
        schema_id = f"{fragment_output_name(fragment)}.schema.json"
        built, defs = export_fragment(model, cache)
        document = FragmentDocument(
            schema_uri="https://json-schema.org/draft/2020-12/schema",
            schema_id=schema_id,
            title=built.title,
            description=built.description,
            properties=built.properties,
            required=built.required,
            additional_properties=built.additional_properties,
            defs=defs if defs else None,
        )
        output_path = output_dir / schema_id
        write_schema(document, output_path)
        sys.stdout.write(f"wrote {output_path.name}\n")
    return 0


def run_list(verdandi_root: Path) -> int:
    """List available schemas."""
    cache: dict[str, BaseModel] = {}
    load_all_levels(verdandi_root, cache, resolve_refs)
    schemas = export_all_schemas(cache)
    for schema_key in sorted(schemas):
        sys.stdout.write(f"{schema_filename(schema_key)}\n")
    return 0


def resolve_mode(
    check: bool,
    list_schemas: bool,
    fragments: bool,
) -> PipelineMode | str:
    """Resolve mutually exclusive flags to a single mode, or return error."""
    if sum([check, list_schemas, fragments]) > 1:
        return "error: --check, --list, and --fragments are mutually exclusive"
    if check:
        return PipelineMode.check
    if list_schemas:
        return PipelineMode.list_schemas
    if fragments:
        return PipelineMode.fragments
    return PipelineMode.generate


def resolve_workspace(
    verdandi_dir: Path | None,
    output_dir: Path | None,
    workspace: Path | None,
    project: str | None,
) -> tuple[Path, Path] | str:
    """Resolve workspace and paths. Returns (verdandi, output) or error string."""
    resolved_workspace = workspace or find_workspace_root(
        Path(__file__).resolve().parent,
    )
    if resolved_workspace is None and not (verdandi_dir and output_dir):
        return (
            "error: cannot find workspace root (no ancestor has verdandi/)\n"
            "  use --workspace, or provide both --verdandi-dir and --output-dir"
        )
    return resolve_paths(verdandi_dir, output_dir, resolved_workspace, project)


def dispatch_mode(context: PipelineContext) -> int:
    """Route to the appropriate pipeline mode."""
    verdandi, output = context_to_paths(context)
    if context.mode == PipelineMode.check:
        return run_check(verdandi, output)
    if context.mode == PipelineMode.list_schemas:
        return run_list(verdandi)
    if context.mode == PipelineMode.fragments:
        return run_fragments(verdandi, output)
    return run_all(verdandi, output)


def resolve_context(args: PipelineArgs) -> PipelineContext | str:
    """Resolve raw CLI args into a validated pipeline context."""
    mode = resolve_mode(args.check, args.list_schemas, args.fragments)
    if not isinstance(mode, PipelineMode):
        return mode
    verdandi_dir, output_dir, workspace = args_to_paths(args)
    result = resolve_workspace(verdandi_dir, output_dir, workspace, args.project)
    if isinstance(result, str):
        return result
    verdandi, output = result
    return PipelineContext(
        mode=mode,
        verdandi=str(verdandi),
        output=str(output),
    )


def run_pipeline(args: PipelineArgs) -> int:
    """Full pipeline: resolve context, dispatch."""
    context = resolve_context(args)
    if isinstance(context, str):
        sys.stderr.write(context + "\n")
        return 1
    return dispatch_mode(context)
