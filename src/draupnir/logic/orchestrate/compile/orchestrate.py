"""Schema pipeline orchestration — wire all zones together.

Orchestrate level (CC=1-5). Compiles the dependency graph via topological
sort, dispatches each node to its builder, detects $defs from in-degree,
assembles conditionals, and routes pipeline modes.
"""

import sys
from pathlib import Path

import networkx as nx
from pydantic import BaseModel

from draupnir.logic.impure.loader.composed import load_all_levels
from draupnir.logic.impure.pipeline.composed import resolve_paths
from draupnir.logic.impure.pipeline.primitive import fragment_output_name, schema_filename
from draupnir.logic.impure.pipeline.simple import args_to_paths, context_to_paths, find_workspace_root
from draupnir.logic.impure.writer.simple import write_schema
from draupnir.logic.transform.graph_build.composed import build_graph
from draupnir.logic.transform.conditional_build.composed import (
    collect_schema_zone_conditionals,
    collect_section_conditionals,
    iter_schema_sections,
)
from draupnir.logic.transform.graph_build.primitive import cache_key_to_defs_key
from draupnir.logic.transform.schema_build.assembled import (
    build_group,
    build_section,
    build_shallowsection,
    build_simplegroup,
    build_verdandi_field,
    unwrap_zone,
)
from draupnir.logic.transform.schema_build.composed import build_atom
from draupnir.logic.transform.schema_build.primitive import (
    build_enum,
    build_pattern,
    build_simplearray,
)
from draupnir.logic.transform.schema_build.simple import (
    build_array,
    build_element,
    build_superarray,
    build_tuple,
    build_union,
    optional_tuple,
)
from draupnir.logic.transform.zone_collect.simple import build_zone_properties
from draupnir.structure.config.build_context import BuildContext
from draupnir.structure.config.fragments import Fragment
from draupnir.structure.config.pipeline import PipelineArgs, PipelineContext, PipelineMode
from draupnir.structure.model.schema_output import (
    FragmentDocument,
    SchemaDocument,
    SchemaRef,
    SchemaRootConditional,
)
from draupnir.structure.model.top_level import (
    Schema,
    SchemaSections,
    SchemaShallowsections,
)


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


# --- Graph compile loop ---


def compile_graph(
    graph: nx.DiGraph,
) -> tuple[BuildContext, dict[str, BaseModel]]:
    """Walk graph in topological order, build each node, detect $defs.

    Returns (context, defs) where context.built/full hold all results
    and defs holds nodes with in-degree >= 2 (shared across parents).
    Schema-level nodes are skipped — assembled separately.
    """
    dispatch = {
        "pattern": build_pattern,
        "enum": build_enum,
        "atom": build_atom,
        "element": build_element,
        "tuple": build_tuple,
        "union": build_union,
        "field": build_verdandi_field,
        "simplearray": build_simplearray,
        "simplegroup": build_simplegroup,
        "array": build_array,
        "group": build_group,
        "superarray": build_superarray,
        "section": build_section,
        "shallowsection": build_shallowsection,
    }
    order = list(reversed(list(nx.topological_sort(graph))))
    context = BuildContext()
    defs: dict[str, BaseModel] = {}
    for cache_key in order:
        level = graph.nodes[cache_key]["level"]
        if level == "schema":
            continue
        model = graph.nodes[cache_key]["model"]
        result = dispatch[level](model, context)
        context.full[cache_key] = result
        context.built[cache_key] = result
        if graph.in_degree(cache_key) >= 2:
            defs_key = cache_key_to_defs_key(cache_key)
            defs[defs_key] = result
            context.built[cache_key] = SchemaRef(ref=f"#/$defs/{defs_key}")
    return context, defs


# --- Schema assembly ---


def collect_section_zone_properties(
    zones: BaseModel | None,
    context: BuildContext,
) -> tuple[dict[str, BaseModel], list[str]]:
    """Collect properties and required keys from a schema zone set.

    Handles .required and .optional zone dicts. Each zone dict value
    is a RootModel[str] section ref — looked up from context.built.
    """
    if zones is None:
        return {}, []
    req_dict = unwrap_zone(zones.required)
    opt_dict = unwrap_zone(zones.optional)
    req_props = build_zone_properties(req_dict, context) if req_dict else {}
    opt_props = build_zone_properties(opt_dict, context) if opt_dict else {}
    return {**req_props, **opt_props}, list(req_props.keys())


def assemble_schema(
    cache_key: str,
    model: BaseModel,
    context: BuildContext,
    defs: dict[str, BaseModel],
) -> SchemaDocument:
    """Assemble a SchemaDocument from a compiled schema model.

    Collects section properties from sections + shallowsections zones,
    builds required list, attaches $defs.
    """
    sec_props, sec_req = collect_section_zone_properties(model.sections, context)
    shallow_props, shallow_req = collect_section_zone_properties(
        model.shallowsections, context,
    )
    properties = {**sec_props, **shallow_props}
    required_keys = sec_req + shallow_req
    schema_name = cache_key.split("/", 1)[1]
    return SchemaDocument(
        schema_uri="https://json-schema.org/draft/2020-12/schema",
        schema_id=schema_name,
        title=model.title.root,
        description=model.description.root,
        required=optional_tuple(required_keys),
        properties=properties,
        additional_properties=False,
        defs=defs or None,
    )


def assemble_fragment(
    cache_key: str,
    context: BuildContext,
    defs: dict[str, BaseModel],
) -> FragmentDocument:
    """Assemble a FragmentDocument from a compiled cache entry.

    Uses context.full for the root (in case it's a SchemaRef in context.built).
    """
    root_schema = context.full[cache_key]
    fragment_name = cache_key.replace("/", "_")
    return FragmentDocument(
        schema_uri="https://json-schema.org/draft/2020-12/schema",
        schema_id=f"include_{fragment_name}",
        title=root_schema.title or fragment_name,
        description=root_schema.description or "",
        properties={"items": root_schema} if hasattr(root_schema, "items") else {},
        defs=defs or None,
    )


def export_all_schemas(
    graph: nx.DiGraph,
    context: BuildContext,
    defs: dict[str, BaseModel],
) -> dict[str, SchemaDocument]:
    """Assemble SchemaDocuments for all schema-level nodes in the graph."""
    schemas: dict[str, SchemaDocument] = {}
    for cache_key in graph.nodes:
        if graph.nodes[cache_key]["level"] != "schema":
            continue
        model = graph.nodes[cache_key]["model"]
        schemas[cache_key] = assemble_schema(cache_key, model, context, defs)
    return schemas


def export_fragments(
    context: BuildContext,
    defs: dict[str, BaseModel],
) -> dict[str, FragmentDocument]:
    """Assemble FragmentDocuments for all registered fragments."""
    fragments: dict[str, FragmentDocument] = {}
    for fragment in Fragment:
        if fragment.value in context.full:
            fragments[fragment.name] = assemble_fragment(
                fragment.value, context, defs,
            )
    return fragments


# --- Pipeline modes ---


def load_and_compile(
    verdandi_root: Path,
) -> tuple[nx.DiGraph, BuildContext, dict[str, BaseModel]] | str:
    """Load all levels, build graph, compile. Returns (graph, ctx, defs) or error."""
    cache: dict[str, BaseModel] = {}
    errors = load_all_levels(verdandi_root, cache)
    if errors:
        return "\n".join(errors)
    graph = build_graph(cache)
    context, defs = compile_graph(graph)
    return graph, context, defs


def run_all(
    verdandi_root: Path,
    output_dir: Path,
) -> int:
    """Load everything, export all schemas, write all files."""
    result = load_and_compile(verdandi_root)
    if isinstance(result, str):
        sys.stderr.write(result + "\n")
        return 1
    graph, context, defs = result
    schemas = export_all_schemas(graph, context, defs)
    for cache_key, document in schemas.items():
        write_schema(document, output_dir / schema_filename(cache_key))
    fragments = export_fragments(context, defs)
    for name, document in fragments.items():
        write_schema(document, output_dir / f"{name.replace('_', '-')}.schema.json")
    return 0


def check_schema_drift(
    schemas: dict[str, SchemaDocument],
    output_dir: Path,
) -> list[str]:
    """Compare compiled schemas against on-disk. Returns list of drift messages."""
    messages: list[str] = []
    for cache_key, document in schemas.items():
        path = output_dir / schema_filename(cache_key)
        if not path.exists():
            messages.append(f"missing: {path}")
            continue
        expected = document.model_dump_json(by_alias=True, exclude_none=True, indent=2)
        if path.read_text().rstrip() != expected:
            messages.append(f"drifted: {path}")
    return messages


def run_check(
    verdandi_root: Path,
    output_dir: Path,
) -> int:
    """Check for drift without writing."""
    result = load_and_compile(verdandi_root)
    if isinstance(result, str):
        sys.stderr.write(result + "\n")
        return 1
    graph, context, defs = result
    schemas = export_all_schemas(graph, context, defs)
    messages = check_schema_drift(schemas, output_dir)
    for message in messages:
        sys.stderr.write(message + "\n")
    return 1 if messages else 0


def run_fragments(
    verdandi_root: Path,
    output_dir: Path,
) -> int:
    """Export standalone include-fragment schemas."""
    result = load_and_compile(verdandi_root)
    if isinstance(result, str):
        sys.stderr.write(result + "\n")
        return 1
    _graph, context, defs = result
    fragments = export_fragments(context, defs)
    for name, document in fragments.items():
        write_schema(document, output_dir / f"{name.replace('_', '-')}.schema.json")
    return 0


def run_list(verdandi_root: Path) -> int:
    """List available schemas."""
    cache: dict[str, BaseModel] = {}
    errors = load_all_levels(verdandi_root, cache)
    if errors:
        sys.stderr.write("\n".join(errors) + "\n")
        return 1
    for cache_key in sorted(cache):
        if cache_key.startswith("schema/"):
            sys.stdout.write(cache_key + "\n")
    return 0


# --- CLI routing (unchanged) ---


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
