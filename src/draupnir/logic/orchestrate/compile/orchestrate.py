"""Schema pipeline orchestration — wire all zones together.

Orchestrate level (CC=1-5). Chains dispatch table, composed builders,
tree_walk analysis, and export assembly. This is the single orchestrate
module — all cross-zone wiring lives here.

NOTE: Schema building and export functions have been removed.
The recursive dispatch approach (build_or_ref, build_model, resolve_handler,
export_schema, export_fragment) is dead. Replacement: network graph approach
that uses topological sort for build order and in-degree for $defs detection.
Pipeline modes (run_all, run_check, etc.) are stubs awaiting the new graph
compiler.
"""

import sys
from pathlib import Path

from draupnir.logic.transform.conditional_build.composed import (
    collect_schema_zone_conditionals,
    collect_section_conditionals,
    iter_schema_sections,
)
from draupnir.structure.config.pipeline import PipelineArgs, PipelineContext, PipelineMode
from draupnir.structure.model.schema_output import SchemaRootConditional
from draupnir.structure.model.top_level import (
    Schema,
    SchemaSections,
    SchemaShallowsections,
)
from draupnir.logic.impure.pipeline.composed import resolve_paths
from draupnir.logic.impure.pipeline.simple import args_to_paths, context_to_paths, find_workspace_root


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


# --- Pipeline modes (stubs — awaiting graph compiler) ---


def run_all(
    verdandi_root: Path,
    output_dir: Path,
) -> int:
    """Load everything, export all schemas, write all files."""
    sys.stderr.write("error: schema compiler not yet implemented (graph approach pending)\n")
    return 1


def run_check(
    verdanni_root: Path,
    output_dir: Path,
) -> int:
    """Check for drift without writing."""
    sys.stderr.write("error: schema compiler not yet implemented (graph approach pending)\n")
    return 1


def run_fragments(
    verdandi_root: Path,
    output_dir: Path,
) -> int:
    """Export standalone include-fragment schemas."""
    sys.stderr.write("error: schema compiler not yet implemented (graph approach pending)\n")
    return 1


def run_list(verdandi_root: Path) -> int:
    """List available schemas."""
    sys.stderr.write("error: schema compiler not yet implemented (graph approach pending)\n")
    return 1


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
        verdanni=str(verdandi),
        output=str(output),
    )


def run_pipeline(args: PipelineArgs) -> int:
    """Full pipeline: resolve context, dispatch."""
    context = resolve_context(args)
    if isinstance(context, str):
        sys.stderr.write(context + "\n")
        return 1
    return dispatch_mode(context)
