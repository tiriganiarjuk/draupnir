# Draupnir -- CONTEXT_MAP

## 1. Purpose Statement

Draupnir is a schema generator that reads Verdandi YAML composition hierarchies (15 level directories, ~348 files in `tools/verdandi/`) and produces JSON Schema documents (13 schemas in `schemas/`) plus HTML sidecar visualizations. It replaces the monolithic `tools/agent_schema.py` (1710 lines) with a structured, functional, Gleipnir-compliant architecture built on frozen Pydantic models, supply-driven loading, and strict pure/impure separation. This CONTEXT_MAP helps new agents orient to where knowledge about draupnir lives across the workspace and helps working LLMs know exactly which file to read when they need to refresh specific understanding mid-session.

---

## 2. Primary References

| Resource | Path | What It Contains | When to Read |
|----------|------|------------------|--------------|
| Context Summary | `context/draupnir.md` | Complete architecture overview, pipeline phases, tier hierarchy, design decisions D1-D11, relationship to other tools, reconciliation log with enrichments from 7 documentation files | First read for any session touching draupnir; the single most comprehensive reference |
| QUICKSTART | `tools/draupnir/QUICKSTART.md` | How to run, input/output, architecture overview, source layout, loading pipeline, export pipeline, anti-patterns, key invariants | When you need to run draupnir or need a compact architecture refresher |
| CLAUDE.md | `tools/draupnir/CLAUDE.md` | Anti-pattern watchlist (13 documented failure modes), context refresh protocol, Gleipnir discipline, FP principles, recovery source table | Before writing any code; after any compaction; when hitting guardrail violations |
| DRAUPNIR_REDESIGN | `tools/draupnir/DRAUPNIR_REDESIGN.md` (~57K) | Full design document: toolcompose-to-Verdandi migration, model definitions, loading strategy, export strategy, $defs mechanism, gated build plan, anti-pattern watchlist | When you need deep architectural rationale or are implementing new features |
| TOOL_BUILDING (draupnir sections) | `definitions/TOOL_BUILDING.md` (Section 0, anti-patterns section) | Pipeline integration: how draupnir fits in the definition authoring pipeline, invocation commands, nornir rebuild after schema generation | When you need to understand draupnir's role in the end-to-end tool building pipeline |
| Discrepancy Alerts | `context/discrepancy_ALERT_draupnir.md` | 3 known discrepancies between documentation and implementation (agent_schema.py still on disk, stale level names in Quick Reference, "8-level" reference in D3) | When investigating inconsistencies or before cleanup work |

---

## 3. Documentation References

All `documentation/` files that cover draupnir topics, identified from the DOCUMENT_INDEX cross-references.

| Document | Path | Relevance to Draupnir | Freshness Note |
|----------|------|-----------------------|----------------|
| Rebuild STATUS | `documentation/pipeline/CRITICAL_DECISIONS.md` | Design decisions D1-D11, pipeline status, draupnir rebuild tracking | Partially updated during reconciliation: "8 levels" corrected to 14 in some places; D3 still references "8-level hierarchy" (see ALERT 3) |
| Agent and Skill Generation | `documentation/operations/AGENT_AND_SKILL_GENERATION.md` | Pipeline context: old TOML system dismantled, current pipeline flow through draupnir, terminology migration | Current; references draupnir as the active schema generator |
| Agent Decomposition | `documentation/toolcompose/AGENT_DECOMPOSITION.md` | 10-agent inventory, shared 10-section structure, schema requirements draupnir must satisfy | Current; structural analysis that informed schema design |
| Hierarchy Rebuild Design | `documentation/toolcompose/HIERARCHY_REBUILD_DESIGN.md` | Design decisions that drove the current 15-level system, level split rationale, compile-time enforcement rules | Updated during reconciliation: level table corrected from 12 to 15 levels |
| Schema Composition Explained | `documentation/toolcompose/SCHEMA_COMPOSITION_EXPLAINED_BY_LLM_FOR_LLM.md` | LLM-oriented operational guide: 5 documented mistake patterns, hierarchy as capability ladder, generator should enforce not fall back | Updated during reconciliation: "How the Generator Works" rewritten for current architecture; Quick Reference table still uses old level names (see ALERT 2) |
| Tool Compose Reasoning | `documentation/toolcompose/TOOL_COMPOSE_REASONING.md` | Multilayered constraint architecture, constrained tool pattern, capability intersection model, two-stage resolve-then-format rationale | Current; design rationale that explains why draupnir's output structure matters |
| Why Schema Composition | `documentation/toolcompose/WHY_SCHEMA_COMPOSITION_IS_THE_KEY.md` | Design philosophy: lifecycle stage modeling, DAG gets schema validation for free, hierarchical locking | Updated during reconciliation: level table corrected from 5 to current 15 levels |
| Definition Format | `documentation/pipeline/DEFINITION_FORMAT.md` | Full agent definition tree spec (all 6 sections) that draupnir schemas validate | Current; the authoritative format spec |

---

## 4. Schema References

Schemas in `schemas/` that relate to draupnir's input or output.

### Produced by Draupnir (13 schemas from `tools/verdandi/schema/*.yaml`)

| Schema File | Pipeline Stage |
|-------------|---------------|
| `schemas/agent-raw-definition.schema.json` | Entry point: validates authored TOML definitions |
| `schemas/agent-paths-resolved.schema.json` | After path absolutization |
| `schemas/agent-includes-merged.schema.json` | After @include expansion |
| `schemas/agent-permissions-resolved.schema.json` | After permission calculation |
| `schemas/agent-instructions-reduced.schema.json` | After instruction processing |
| `schemas/agent-examples-reduced.schema.json` | After example processing |
| `schemas/agent-guardrails-reduced.schema.json` | After guardrail processing |
| `schemas/agent-success-reduced.schema.json` | After success/failure processing |
| `schemas/agent-criteria-merged.schema.json` | After criteria merging |
| `schemas/agent-execution-merged.schema.json` | After execution merging |
| `schemas/agent-universal-format.schema.json` | Final universal format output |
| `schemas/agent-universal-render.schema.json` | Render-ready universal format |
| `schemas/agent-anthropic-render.schema.json` | Anthropic-specific render format |

### Not Produced by Draupnir (other generators)

| Schema File | Generator |
|-------------|-----------|
| `schemas/glossary.schema.json` | `tools/regenerate_quality_standards.py` |
| `schemas/qc-report.schema.json` | `tools/regenerate_quality_standards.py` |
| `schemas/interview.schema.json` | Manual / interview system |
| `schemas/interview-index.schema.json` | Manual / interview system |
| `schemas/summaries.schema.json` | Manual / enrichment pipeline |
| `schemas/decomposition.schema.json` | Manual / enrichment pipeline |
| `schemas/entity-suggestion.schema.json` | Manual / truth system |

---

## 5. Upstream Dependencies

What draupnir reads FROM.

| Dependency | Path | Description |
|------------|------|-------------|
| Verdandi YAML files | `tools/verdandi/{level}/*.yaml` | 15 level directories (pattern, enum, atom, element, union, tuple, field, simplearray, simplegroup, array, group, superarray, section, shallowsection, schema) containing ~348 YAML composition type files. This is draupnir's sole input source. |
| Verdandi composition rules | `tools/verdandi/COMPOSITION_RULES.md` | Hierarchy enforcement rules and tier containment constraints that draupnir validates at compile time via typed ref aliases |
| Gleipnir rules | `tools/draupnir/.gleipnir/rules.toml` | Structural constraints enforced at runtime — violations mean the function does too much |
| Gleipnir tests config | `tools/draupnir/.gleipnir/tests.toml` | Test configuration for guardrail checks |

---

## 6. Downstream Consumers

What reads draupnir's output.

| Consumer | Path | How It Uses Draupnir Output |
|----------|------|-----------------------------|
| nornir (Rust validation) | `tools/nornir/` | Embeds draupnir's JSON Schema files at compile time (`cargo build --release`). Uses them as validation rules for agent definition TOML files. After draupnir regenerates schemas, nornir must be rebuilt to embed the updated versions. |
| transform_to_universal | `tools/transform_to_universal/` | The 11-stage DAG resolver that transforms raw definitions through pipeline stages. References the same schemas draupnir produces to validate at each stage boundary. |
| inspect_schema.py | `tools/inspect_schema.py` | Standalone script that reads ONLY the generated JSON Schema output (not YAML input) and produces HTML sidecar visualizations. Called by draupnir's `writer.py` during generation. Its independence serves as verification: it shows what the generator actually produced, not what YAML intended. |
| scaffold_definition.py | `tools/scaffold_definition.py` | Reads `agent-raw-definition.schema.json` to generate fill-in-the-blanks TOML scaffolds for definition authoring. |
| nornir check tools | `tools/nornir/target/release/` binaries (e.g., `check_raw_definition`, `check_paths_resolved`) | CLI validation binaries that use the embedded schemas to validate pipeline stage outputs. |

---

## 7. Source Code Map

All source files under `src/draupnir/`. Uses v2 zone architecture with level bands.

**NOTE (2026-04-01):** The codebase is mid-transition to a network graph approach. All recursive dispatch code has been deleted. Pipeline modes are stubs awaiting the graph compiler. The structure below reflects the CURRENT state.

### Entry Point

| File | Purpose |
|------|---------|
| `cli.py` | CLI argument parsing, entry point (`draupnir.cli:main`) |
| `logic/entry_point.py` | Delegates to orchestrate |

### structure/ — Frozen Pydantic Data Models

| File | Purpose |
|------|---------|
| `structure/model/fields.py` | Tier 1: Pattern, Atom, Enum, Element, Union_ + ref type aliases |
| `structure/model/simple_containers.py` | Tier 2: VerdandiField, Tuple_, Simplearray, Simplegroup |
| `structure/model/complex_containers.py` | Tier 3: Array, Group, Superarray + supporting types |
| `structure/model/top_level.py` | Tier 4: Section, Shallowsection, Schema + zone containers |
| `structure/model/conditionals.py` | ConditionalWhen predicates |
| `structure/model/field.py` | SemanticBlock, ConstraintRule |
| `structure/model/schema_output.py` | JSON Schema output models (SchemaDocument, SchemaField, SchemaObject, SchemaRef, etc.) |
| `structure/config/levels.py` | Level enum — level name → model class mapping |
| `structure/config/fragments.py` | Fragment enum — output names → cache keys |
| `structure/config/pipeline.py` | PipelineMode, PipelineArgs, PipelineContext |

### logic/impure/ — IO boundary

| File | Purpose |
|------|---------|
| `logic/impure/loader/ffi.py` | Gate FFI wrapper — `gate_validate(file_path, level_name, schema_dir)` |
| `logic/impure/loader/primitive.py` | Path/string helpers: `parse_cache_key`, `level_file_path`, `level_model` |
| `logic/impure/dispatch/primitive.py` | `cache_key_to_defs_key` — string transform for $defs naming |
| `logic/impure/pipeline/primitive.py` | Output naming: `schema_filename`, `fragment_output_name` |
| `logic/impure/pipeline/simple.py` | Path resolution: `args_to_paths`, `find_workspace_root` |
| `logic/impure/pipeline/composed.py` | `resolve_paths` |
| `logic/impure/writer/primitive.py` | `serialize_schema` — model_dump_json boundary |
| `logic/impure/writer/simple.py` | `write_schema` — file write |

### logic/transform/ — Pure model-to-model conversion

| File | Purpose |
|------|---------|
| `logic/transform/schema_build/primitive.py` | `build_enum`, `build_simplearray` — uses `built` dict |
| `logic/transform/schema_build/simple.py` | `build_atom`, `build_element`, `build_union`, `build_array`, `build_superarray`, `build_tuple` — all use `built` dict |
| `logic/transform/schema_build/assembled.py` | `build_simplegroup`, `build_group`, `build_section`, `build_shallowsection` — all use `built` dict |
| `logic/transform/zone_collect/simple.py` | `collect_required_optional`, `build_zone_properties` — uses `built` dict |
| `logic/transform/zone_collect/composed.py` | `collect_conditional` — uses `built` dict |
| `logic/transform/conditional_build/primitive.py` | `build_only_when`, `build_always_when`, `build_not_when`, path parsing |
| `logic/transform/conditional_build/simple.py` | `dispatch_when_builder`, `build_conditional_entry`, nested conditional builders |
| `logic/transform/conditional_build/composed.py` | `collect_group_conditionals`, `collect_section_conditionals`, `iter_schema_sections` |
| `logic/transform/field_annotate/simple.py` | Field metadata computation |
| `logic/transform/field_annotate/composed.py` | `apply_inline_metadata` |

### logic/orchestrate/ — Wiring layer

| File | Purpose |
|------|---------|
| `logic/orchestrate/compile/dispatch.py` | Type → builder routing table (5 types currently) |
| `logic/orchestrate/compile/orchestrate.py` | **STUB** — CLI routing intact, pipeline modes return error pending graph compiler |

### logic/pure/ — Empty, awaiting graph code

The `pure/` zone directory exists but is empty after cleanup. The network graph implementation will live here.

### DELETED (2026-04-01 cleanup)

These directories/files were removed because they implement the old recursive dispatch approach:
- `logic/transform/ref_resolve/` — dict-walking `resolve_refs`
- `logic/pure/tree_walk/` — `reverse_cache_index`, `count_refs`, `shared_keys`, `iter_child_models`
- `logic/impure/loader/assembled.py` — yaml.safe_load + resolve_refs + model_validate
- `logic/impure/loader/composed.py` — level-ordered iteration with Callable DI
- `logic/transform/schema_build/composed.py` — recursive dispatch functions
- `logic/transform/field_annotate/assembled.py` — Callable-based field builder

### tools/

| File | Purpose |
|------|---------|
| `tools/export_input_schemas.py` | Export 15 input validation schemas from Pydantic models (ref→string transform) |

---

## 8. Context Refresh Guide

For an LLM mid-session that needs to refresh specific understanding.

| If You Need To Understand... | Read This |
|------------------------------|-----------|
| Why recursive dispatch was wrong and what replaces it | `src/draupnir/WHY_NETWORK_GRAPHS_ARE_THE_SOLUTION.md` |
| What failed approaches to avoid | `src/draupnir/WHY_WE_KEEP_GETTING_STUCK.md` |
| How to recover when stuck | `src/draupnir/HOW_TO_GET_UNSTUCK.md` |
| The gate architecture (file validation boundary) | nornir memory: `project_draupnir_input_gates.md` |
| The graph architecture (topological sort, in-degree, $defs) | nornir memory: `project_draupnir_graph_architecture.md` |
| The Verdandi hierarchy (15 levels, 4 tiers, tier containment) | `DRAUPNIR_REDESIGN.md` §1-§4; `tools/verdandi/COMPOSITION_RULES.md` |
| Design rationale (why the rebuild happened, what changed) | `DRAUPNIR_REDESIGN.md` §1-§6 |
| Schema output models (JSON Schema shapes produced) | `structure/model/schema_output.py` |
| Existing builders (already converted to `built` dict) | `logic/transform/schema_build/simple.py`, `assembled.py` |
| Regin model generation pattern (for generated input models) | `~/.ai/smidja/regin/src/regin/generate_structures.py`, `codegen_schemas.toml` |
| Pure/impure separation | `CLAUDE.md` "IO Externalization" section |
| Anti-patterns and failure modes | `CLAUDE.md` "You Will Get These Things Wrong" |
| Gleipnir constraints and guardrail discipline | `CLAUDE.md` "Gleipnir" section |

---

## 9. Known Issues / Active Work

### Active: Network Graph Architecture (2026-04-01)

The codebase is mid-transition. All recursive dispatch code has been deleted. Pipeline modes are stubs. The next step is implementing the network graph compiler:

1. **Generated input models** — generate Pydantic models from input schemas (Regin pattern with `datamodel-code-generator`)
2. **New loader** — gate reads file → JSON → `model_validate_json` with generated input models → cache
3. **Graph builder** — NetworkX DiGraph from cache, string refs = edges, models = node attributes
4. **Graph compiler** — topological sort → walk in order → dispatch to existing builders → `built` dict → $defs from in-degree >= 2
5. **Schema export** — assemble SchemaDocument from graph output

See `src/draupnir/WHY_NETWORK_GRAPHS_ARE_THE_SOLUTION.md` for full rationale.

### Gate system

The Rust PyO3 gate (`nornir/gates/gate_verdandi_input/`) is built and working. It reads YAML files, validates against JSON Schema, returns JSON strings. 15 input schemas exported to `schemas/input/`. The gate output JSON is currently discarded — the new loader will use it directly via `model_validate_json`.

### Stale documentation alerts

**ALERT 1:** `tools/agent_schema.py` still on disk (1710-line predecessor). Ask user about retention.
**ALERT 2:** Quick Reference table in `SCHEMA_COMPOSITION_EXPLAINED_BY_LLM_FOR_LLM.md` uses old directory names.
**ALERT 3:** CRITICAL_DECISIONS.md D3 references "8-level hierarchy" (now 15 levels).

### COMPLETED: Schema Zone Unification

Schema model uses `SchemaSections`/`SchemaShallowsections` zone containers. ConditionalWhen has `exists` field. Leading-dot cross-section path detection. Nullable wrapping removed.
