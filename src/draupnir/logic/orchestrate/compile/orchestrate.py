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
from draupnir.logic.impure.pipeline.simple import (
    args_to_paths,
    context_to_paths,
    find_workspace_root,
)
from draupnir.logic.impure.writer.simple import write_schema
from draupnir.logic.pure.cross_section.composed import (
    adapt_edge_when,
    collect_section_graph_conditionals,
)
from draupnir.logic.pure.cross_section.simple import (
    build_root_conditional,
    resolve_cross_section_mode,
)
from draupnir.logic.pure.graph_build.composed import build_graph, subtree_build_order
from draupnir.logic.pure.graph_build.primitive import cache_key_to_defs_key
from draupnir.logic.pure.graph_build.simple import schema_shared_keys
from draupnir.logic.transform.schema_assembly.assembled import assemble_schema
from draupnir.logic.transform.schema_assembly.composed import assemble_fragment
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


# --- Conditional assembly ---


def build_edge_zone_conditional(
    edge_data: dict[str, BaseModel | str | None],
    section_name: str,
) -> SchemaRootConditional | None:
    """Build a zone conditional from a schema→section edge, or None.

    Returns None if the edge is not a conditional zone or if the when
    condition is not cross-section.
    """
    if edge_data["zone"] != "conditional":
        return None
    adapted_only = adapt_edge_when(edge_data.get("only_when"))
    adapted_always = adapt_edge_when(edge_data.get("always_when"))
    adapted_not = adapt_edge_when(edge_data.get("not_when"))
    resolved = resolve_cross_section_mode(adapted_only, adapted_always, adapted_not)
    if resolved is None:
        return None
    active, mode = resolved
    return build_root_conditional(active, section_name, (), mode)


def collect_graph_conditionals(
    schema_key: str,
    graph: nx.DiGraph,
) -> list[SchemaRootConditional]:
    """Collect cross-section conditionals by walking graph edges.

    Iterates schema → section edges for zone conditionals, then
    delegates section → group → field traversal to the composed layer.
    """
    results: list[SchemaRootConditional] = []
    for section_key in graph.successors(schema_key):
        if graph.nodes[section_key]["level"] != "section":
            continue
        schema_edge = graph[schema_key][section_key]
        section_name = schema_edge["name"]
        zone_cond = build_edge_zone_conditional(schema_edge, section_name)
        if zone_cond is not None:
            results.append(zone_cond)
        results.extend(collect_section_graph_conditionals(
            section_key, section_name, graph,
        ))
    return results


# --- Per-schema compile ---


def compile_subtree(
    root_key: str,
    graph: nx.DiGraph,
    shared: frozenset[str],
) -> tuple[BuildContext, dict[str, BaseModel]]:
    """Build a subtree with per-root $defs promotion.

    Walks descendants of root_key in topological order. Nodes in the
    shared set are promoted to $defs; all others are inlined. Returns
    a fresh context and defs scoped to this root.
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
    order = subtree_build_order(root_key, graph)
    context = BuildContext()
    defs: dict[str, BaseModel] = {}
    for cache_key in order:
        level = graph.nodes[cache_key]["level"]
        model = graph.nodes[cache_key]["model"]
        result = dispatch[level](model, context)
        context.full[cache_key] = result
        context.built[cache_key] = result
        if cache_key in shared:
            defs_key = cache_key_to_defs_key(cache_key)
            defs[defs_key] = result
            context.built[cache_key] = SchemaRef(ref=f"#/$defs/{defs_key}")
    return context, defs


# --- Schema export ---


def export_all_schemas(
    graph: nx.DiGraph,
) -> dict[str, SchemaDocument]:
    """Assemble SchemaDocuments for all schema-level nodes in the graph."""
    schemas: dict[str, SchemaDocument] = {}
    for cache_key in graph.nodes:
        if graph.nodes[cache_key]["level"] != "schema":
            continue
        model = graph.nodes[cache_key]["model"]
        shared = schema_shared_keys(cache_key, graph)
        context, defs = compile_subtree(cache_key, graph, shared)
        schema_doc = assemble_schema(cache_key, model, graph, context, defs)
        conditionals = collect_graph_conditionals(cache_key, graph)
        if conditionals:
            schema_doc = schema_doc.model_copy(update={"all_of": tuple(conditionals)})
        schemas[cache_key] = schema_doc
    return schemas


def export_fragments(
    graph: nx.DiGraph,
) -> dict[str, FragmentDocument]:
    """Assemble FragmentDocuments for all registered fragments."""
    fragments: dict[str, FragmentDocument] = {}
    for fragment in Fragment:
        fragment_key = fragment.value
        if fragment_key not in graph.nodes:
            continue
        shared = schema_shared_keys(fragment_key, graph)
        context, defs = compile_subtree(fragment_key, graph, shared)
        fragments[fragment.name] = assemble_fragment(
            fragment_key, fragment.name, context, defs,
        )
    return fragments


# --- Pipeline modes ---


def load_and_build_graph(
    verdandi_root: Path,
) -> nx.DiGraph | str:
    """Load all levels, build graph. Returns graph or error string."""
    cache: dict[str, BaseModel] = {}
    errors = load_all_levels(verdandi_root, cache)
    if errors:
        return "\n".join(errors)
    return build_graph(cache)


def run_generate(
    verdandi_root: Path,
    output_dir: Path,
) -> int:
    """Load, build graph, export all schemas and fragments, write to disk."""
    result = load_and_build_graph(verdandi_root)
    if isinstance(result, str):
        sys.stderr.write(result + "\n")
        return 1
    graph = result
    schemas = export_all_schemas(graph)
    for cache_key, document in schemas.items():
        write_schema(document, output_dir / schema_filename(cache_key))
    fragments = export_fragments(graph)
    for name, document in fragments.items():
        write_schema(document, output_dir / f"{name.replace('_', '-')}.schema.json")
    return 0


def run_check(
    verdandi_root: Path,
    output_dir: Path,
) -> int:
    """Load, build graph, compare against on-disk schemas."""
    result = load_and_build_graph(verdandi_root)
    if isinstance(result, str):
        sys.stderr.write(result + "\n")
        return 1
    schemas = export_all_schemas(result)
    messages = check_schema_drift(schemas, output_dir)
    for message in messages:
        sys.stderr.write(message + "\n")
    return 1 if messages else 0


def run_fragments(
    verdandi_root: Path,
    output_dir: Path,
) -> int:
    """Load, build graph, export and write fragments only."""
    result = load_and_build_graph(verdandi_root)
    if isinstance(result, str):
        sys.stderr.write(result + "\n")
        return 1
    fragments = export_fragments(result)
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
