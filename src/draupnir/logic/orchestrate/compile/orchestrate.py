"""Schema pipeline orchestration — compile, export, and run pipeline modes.

Orchestrate level (CC=1-5). Wires together the pure (graph analysis),
transform (schema building), and impure (I/O) layers into a complete
pipeline. The main data flow:

  load_all_levels → build_graph → [per schema: compile_subtree → assemble_schema
  → collect_graph_conditionals → merge allOf] → write_schema

Key architectural decisions:
- Per-schema compilation: each schema root gets its own BuildContext and
  $defs set via compile_subtree + schema_shared_keys. This ensures $defs
  only contain types actually shared within that schema's subtree.
- Dispatch table: lives inside compile_subtree as a local dict, not at
  module level (gleipnir bans module-level constants in logic zones).
- Cross-section conditionals: collected via graph traversal AFTER assembly,
  then merged via model_copy because they require path information from
  the schema→section→group edge chain that assembly doesn't track.
- Pipeline modes: generate (default), check (drift detection), list
  (schema names), fragments (include files only). Resolved from mutually
  exclusive CLI flags.
"""

import sys
from pathlib import Path

import networkx as nx
from pydantic import BaseModel

from draupnir.logic.impure.loader.composed import load_all_levels
from draupnir.logic.impure.paths_locate.primitive import locate_draupnir_paths
from draupnir.logic.impure.pipeline.composed import check_schema_drift
from draupnir.logic.pure.serialize.simple import named_documents
from draupnir.logic.impure.pipeline.simple import (
    args_to_paths,
    context_to_paths,
    find_workspace_root,
    list_projects,
    optional_path,
    resolve_paths,
)
from draupnir.logic.impure.writer.simple import write_schemas
from draupnir.logic.pure.cross_section.composed import (
    adapt_edge_when,
    collect_section_graph_conditionals,
)
from draupnir.logic.pure.cross_section.simple import (
    build_root_conditional,
    resolve_cross_section_mode,
)
from draupnir.logic.pure.graph_build.composed import (
    build_graph,
    node_predicate_violations,
    subtree_build_order,
)
from draupnir.logic.pure.graph_build.primitive import cache_key_to_defs_key
from draupnir.logic.pure.graph_build.simple import schema_shared_keys
from draupnir.logic.pure.schema_locate.primitive import json_schema_document_schema
from draupnir.logic.orchestrate.compile.dispatch import BUILDER_DISPATCH
from draupnir.logic.transform.schema_assembly.assembled import assemble_schema
from draupnir.logic.transform.schema_assembly.composed import assemble_fragment
from draupnir.logic.transform.schema_build.composed import resolve_array_constraints
from draupnir.structure.config.build_context import BuildContext
from draupnir.structure.config.draupnir_paths import DraupnirPaths
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

    Handles the case where an entire section is conditional (e.g.,
    "include this section only_when some cross-section field equals X").
    Returns None if the edge zone isn't "conditional" or if the when
    condition references a same-section field (those are handled inline
    by the transform layer's conditional_build).
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

    Two sources of cross-section conditionals:
    1. Zone conditionals: schema→section edges where zone="conditional"
       (entire section is conditional on a cross-section field)
    2. Field conditionals: section→group→field edges with dotted-path
       when.field values (individual fields conditional on cross-section)

    Only section-level successors are walked (not shallowsections) because
    the old pipeline's conditional collection only traversed sections.
    The level filter ensures parity with the baseline output.
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

    Walks descendants of root_key in topological order (guaranteed by
    subtree_build_order filtering the global topo sort). Each node is
    dispatched to its level-specific builder. The builder reads pre-built
    children from context.built — because we process in topo order, all
    children are built before their parents.

    Shared nodes (in-degree >= 2 within this subtree) are promoted to
    $defs: stored in the defs dict and replaced with a SchemaRef in
    context.built. context.full always retains the complete schema for
    functions that need actual field values (e.g., element inheriting
    atom's pattern, field metadata needing inner type's description).
    """
    array_levels = frozenset({"simplearray", "array", "superarray"})
    order = subtree_build_order(root_key, graph)
    context = BuildContext()
    defs: dict[str, BaseModel] = {}
    for cache_key in order:
        level = graph.nodes[cache_key]["level"]
        model = graph.nodes[cache_key]["model"]
        result = BUILDER_DISPATCH[level](model, context)
        if level in array_levels:
            result = result.model_copy(update=resolve_array_constraints(model))
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
    """Assemble SchemaDocuments for all schema-level nodes in the graph.

    Each schema is compiled independently: fresh BuildContext, per-schema
    shared set, per-schema $defs. Cross-section conditionals are collected
    after assembly and merged via model_copy because they require graph
    traversal information that the assembly layer doesn't have access to.
    """
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
    """Assemble FragmentDocuments for all registered fragments.

    Fragments are standalone include files for TOML. The Fragment enum
    defines the known fragments and their cache keys. Each fragment is
    compiled independently like schemas, but assembled via assemble_fragment
    which handles the array-wrapping and group-inlining differences.
    """
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
    paths: DraupnirPaths,
) -> nx.DiGraph | str:
    """Load all Verdandi YAML levels into cache, then build the dependency graph.

    Returns the DiGraph on success or an error string on load failure.
    The string-or-graph return type avoids exceptions for expected errors
    (missing files, validation failures) while keeping the caller simple.
    """
    cache: dict[str, BaseModel] = {}
    errors = load_all_levels(verdandi_root, cache, paths.input_schema_dir)
    if errors:
        return "\n".join(errors)
    graph = build_graph(cache)
    violations = [
        violation
        for node in graph.nodes
        for violation in node_predicate_violations(graph, node)
    ]
    if violations:
        return "\n".join(violations)
    return graph


def run_generate(
    verdandi_root: Path,
    output_dir: Path,
    paths: DraupnirPaths,
) -> int:
    """Full generation pipeline: load → graph → compile → assemble → write.

    Writes both schemas (13 for agent-builder) and fragments (7) to
    the output directory. Fragment filenames use hyphens (underscores
    replaced) to match the established naming convention.
    """
    result = load_and_build_graph(verdandi_root, paths)
    if isinstance(result, str):
        sys.stderr.write(result + "\n")
        return 1
    schemas = export_all_schemas(result)
    fragments = export_fragments(result)
    documents = named_documents(schemas, fragments)
    errors = write_schemas(documents, output_dir, json_schema_document_schema(paths))
    if errors:
        sys.stderr.write("\n".join(errors) + "\n")
        return 1
    for filename in documents:
        sys.stdout.write(f"  wrote {filename}\n")
    sys.stdout.write(f"\n{len(schemas)} schemas + {len(fragments)} fragments -> {output_dir}\n")
    return 0


def run_check(
    verdandi_root: Path,
    output_dir: Path,
    paths: DraupnirPaths,
) -> int:
    """Drift check: compile schemas in memory and compare against on-disk files.

    Returns 0 if all on-disk schemas match compiled output, 1 if any
    differ or are missing. Used by CI to detect stale schema files.
    """
    result = load_and_build_graph(verdandi_root, paths)
    if isinstance(result, str):
        sys.stderr.write(result + "\n")
        return 1
    documents = named_documents(export_all_schemas(result), export_fragments(result))
    messages = check_schema_drift(documents, output_dir, json_schema_document_schema(paths))
    for message in messages:
        sys.stderr.write(message + "\n")
    return 1 if messages else 0


def run_fragments(
    verdandi_root: Path,
    output_dir: Path,
    paths: DraupnirPaths,
) -> int:
    """Fragment-only generation: skip full schemas, write only include files."""
    result = load_and_build_graph(verdandi_root, paths)
    if isinstance(result, str):
        sys.stderr.write(result + "\n")
        return 1
    errors = write_schemas(
        named_documents({}, export_fragments(result)), output_dir,
        json_schema_document_schema(paths),
    )
    if errors:
        sys.stderr.write("\n".join(errors) + "\n")
        return 1
    return 0


def run_list(
    verdandi_root: Path,
    output_dir: Path,
    paths: DraupnirPaths,
) -> int:
    """List available schema names from the Verdandi source directory.

    Loads all levels but only prints cache keys starting with "schema/".
    output_dir is accepted for signature compatibility but not used.
    """
    cache: dict[str, BaseModel] = {}
    errors = load_all_levels(verdandi_root, cache, paths.input_schema_dir)
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
    """Resolve mutually exclusive CLI flags to a single PipelineMode.

    Returns error string if more than one flag is set. Default mode is
    generate (no flags). The sum check catches combinations like
    --check --fragments which would be ambiguous.
    """
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
    """Resolve workspace root and derive Verdandi/output paths.

    Auto-discovers workspace by walking up from this file's location. An
    explicit source/output pair needs no workspace. Returns an error string
    when neither a workspace nor the explicit pair is available.
    """
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
    """Resolve raw CLI args into a validated pipeline context.

    Chains mode resolution → path resolution → context construction.
    Returns error string at any failure point rather than raising,
    keeping the error handling uniform through the orchestrate layer.
    """
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


def dispatch_mode(
    mode: PipelineMode, verdandi: Path, output: Path, paths: DraupnirPaths,
) -> int:
    """Route a resolved pipeline mode to its handler function."""
    match mode:
        case PipelineMode.generate:
            return run_generate(verdandi, output, paths)
        case PipelineMode.check:
            return run_check(verdandi, output, paths)
        case PipelineMode.list_schemas:
            return run_list(verdandi, output, paths)
        case PipelineMode.fragments:
            return run_fragments(verdandi, output, paths)


def run_target(args: PipelineArgs, paths: DraupnirPaths) -> int:
    """Run one target: resolve its context then dispatch to the mode handler."""
    context = resolve_context(args)
    if isinstance(context, str):
        sys.stderr.write(context + "\n")
        return 1
    verdandi, output = context_to_paths(context)
    return dispatch_mode(context.mode, verdandi, output, paths)


def all_project_targets(args: PipelineArgs) -> list[PipelineArgs] | str:
    """One target per Verdandi project under the workspace root.

    Returns an error string when the workspace cannot be found or holds no
    project: an invocation that would compile nothing is a failure.
    """
    workspace = optional_path(args.workspace) or find_workspace_root(
        Path(__file__).resolve().parent,
    )
    if workspace is None:
        return (
            "error: cannot find workspace root (no ancestor has verdandi/)\n"
            "  use --workspace, or --project, or both --verdandi-dir and --output-dir"
        )
    names = list_projects(workspace / "verdandi")
    if not names:
        return f"error: no Verdandi project found under {workspace / 'verdandi'}"
    return [args.model_copy(update={"project": name}) for name in names]


def pipeline_targets(args: PipelineArgs) -> list[PipelineArgs] | str:
    """What one invocation compiles.

    A named project or an explicit source/output directory pair is one
    target. With neither, every project under the workspace is a target.
    One directory of the pair without the other names no target.
    """
    explicit_dirs = [args.verdandi_dir, args.output_dir]
    if args.project or all(explicit_dirs):
        return [args]
    if any(explicit_dirs):
        return "error: give --verdandi-dir and --output-dir together, or with --project"
    return all_project_targets(args)


def run_pipeline(args: PipelineArgs) -> int:
    """Top-level pipeline entry: run every target, return the worst exit code.

    Draupnir's own locations are worked out here, once, and passed down.
    """
    targets = pipeline_targets(args)
    if isinstance(targets, str):
        sys.stderr.write(targets + "\n")
        return 1
    paths = locate_draupnir_paths()
    return max(run_target(target, paths) for target in targets)
