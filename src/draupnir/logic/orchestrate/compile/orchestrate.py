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
from draupnir.logic.impure.pipeline.composed import check_schema_drift, resolve_paths
from draupnir.logic.pure.serialize.primitive import schema_filename
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
from draupnir.logic.transform.schema_build.composed import (
    build_atom,
    resolve_array_constraints,
)
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
    array_levels = frozenset({"simplearray", "array", "superarray"})
    order = subtree_build_order(root_key, graph)
    context = BuildContext()
    defs: dict[str, BaseModel] = {}
    for cache_key in order:
        level = graph.nodes[cache_key]["level"]
        model = graph.nodes[cache_key]["model"]
        result = dispatch[level](model, context)
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
) -> nx.DiGraph | str:
    """Load all Verdandi YAML levels into cache, then build the dependency graph.

    Returns the DiGraph on success or an error string on load failure.
    The string-or-graph return type avoids exceptions for expected errors
    (missing files, validation failures) while keeping the caller simple.
    """
    cache: dict[str, BaseModel] = {}
    errors = load_all_levels(verdandi_root, cache)
    if errors:
        return "\n".join(errors)
    return build_graph(cache)


def run_generate(
    verdandi_root: Path,
    output_dir: Path,
) -> int:
    """Full generation pipeline: load → graph → compile → assemble → write.

    Writes both schemas (13 for agent-builder) and fragments (7) to
    the output directory. Fragment filenames use hyphens (underscores
    replaced) to match the established naming convention.
    """
    result = load_and_build_graph(verdandi_root)
    if isinstance(result, str):
        sys.stderr.write(result + "\n")
        return 1
    graph = result
    schemas = export_all_schemas(graph)
    for cache_key, document in schemas.items():
        filename = schema_filename(cache_key)
        write_schema(document, output_dir / filename)
        sys.stdout.write(f"  wrote {filename}\n")
    fragments = export_fragments(graph)
    for name, document in fragments.items():
        filename = f"{name.replace('_', '-')}.schema.json"
        write_schema(document, output_dir / filename)
        sys.stdout.write(f"  wrote {filename}\n")
    sys.stdout.write(f"\n{len(schemas)} schemas + {len(fragments)} fragments -> {output_dir}\n")
    return 0


def run_check(
    verdandi_root: Path,
    output_dir: Path,
) -> int:
    """Drift check: compile schemas in memory and compare against on-disk files.

    Returns 0 if all on-disk schemas match compiled output, 1 if any
    differ or are missing. Used by CI to detect stale schema files.
    """
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
    """Fragment-only generation: skip full schemas, write only include files."""
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
    """List available schema names from the Verdandi source directory.

    Loads all levels but only prints cache keys starting with "schema/".
    output_dir is accepted for signature compatibility but not used.
    """
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

    Auto-discovers workspace by walking up from this file's location.
    Falls back to explicit paths if workspace can't be found. Returns
    error string when neither workspace nor explicit paths are available.
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


def run_pipeline(args: PipelineArgs) -> int:
    """Top-level pipeline entry: resolve context then dispatch to mode handler.

    The mode_dispatch dict maps PipelineMode enum values to the run_*
    functions. All mode handlers share the same (verdandi, output) → int
    signature for uniform dispatching.
    """
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
