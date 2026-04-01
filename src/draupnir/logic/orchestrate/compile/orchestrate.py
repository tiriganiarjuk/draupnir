"""Schema pipeline orchestration — compile, export, and run pipeline modes.

Orchestrate level (CC=1-5). Compiles the dependency graph via topological
sort, dispatches each node to its builder, detects $defs from in-degree,
exports assembled schemas and fragments, and routes pipeline modes.
"""

import sys
from pathlib import Path

import networkx as nx
from pydantic import BaseModel

from draupnir.logic.impure.loader.composed import load_all_levels
from draupnir.logic.impure.pipeline.composed import check_schema_drift, resolve_paths
from draupnir.logic.impure.pipeline.primitive import schema_filename
from draupnir.logic.impure.pipeline.simple import args_to_paths, context_to_paths, find_workspace_root
from draupnir.logic.impure.writer.simple import write_schema
from draupnir.logic.transform.graph_build.composed import build_graph
from draupnir.logic.transform.graph_build.primitive import cache_key_to_defs_key
from draupnir.logic.transform.schema_assembly.assembled import assemble_schema
from draupnir.logic.transform.schema_assembly.composed import assemble_fragment
from draupnir.logic.transform.conditional_build.composed import (
    collect_schema_zone_conditionals,
    collect_section_conditionals,
    iter_schema_sections,
)
from draupnir.logic.transform.schema_build.assembled import (
    build_group,
    build_section,
    build_shallowsection,
    build_simplegroup,
    build_verdandi_field,
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
    build_tuple,
    build_union,
)
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


# --- Conditional assembly ---


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
        "superarray": build_array,
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


# --- Schema export ---


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


def run_generate(
    verdandi_root: Path,
    output_dir: Path,
) -> int:
    """Load, compile, export all schemas and fragments, write to disk."""
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


def run_check(
    verdandi_root: Path,
    output_dir: Path,
) -> int:
    """Load, compile, compare against on-disk schemas."""
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
    """Load, compile, export and write fragments only."""
    result = load_and_compile(verdandi_root)
    if isinstance(result, str):
        sys.stderr.write(result + "\n")
        return 1
    _graph, context, defs = result
    fragments = export_fragments(context, defs)
    for name, document in fragments.items():
        write_schema(document, output_dir / f"{name.replace('_', '-')}.schema.json")
    return 0


def run_list(
    verdandi_root: Path,
    output_dir: Path,
) -> int:
    """Load levels and list available schema names. Ignores output_dir."""
    cache: dict[str, BaseModel] = {}
    errors = load_all_levels(verdandi_root, cache)
    if errors:
        sys.stderr.write("\n".join(errors) + "\n")
        return 1
    for cache_key in sorted(cache):
        if cache_key.startswith("schema/"):
            sys.stdout.write(cache_key + "\n")
    return 0


# --- CLI routing ---


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
    """Resolve CLI args and dispatch to the appropriate pipeline mode."""
    context = resolve_context(args)
    if isinstance(context, str):
        sys.stderr.write(context + "\n")
        return 1
    verdandi, output = context_to_paths(context)
    mode_dispatch = {
        PipelineMode.generate: run_generate,
        PipelineMode.check: run_check,
        PipelineMode.list_schemas: run_list,
        PipelineMode.fragments: run_fragments,
    }
    return mode_dispatch[context.mode](verdandi, output)
