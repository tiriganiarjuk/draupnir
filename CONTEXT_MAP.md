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

All source files under `tools/draupnir/src/draupnir/`.

### Entry Point

| File | Purpose | Key Functions/Classes |
|------|---------|----------------------|
| `cli.py` | CLI argument parsing and dispatch | `main()` -- entry point (defined in pyproject.toml as `draupnir.cli:main`); `build_parser()` -- argparse setup with `--all`, `--check`, `--list` modes; `find_workspace_root()` -- auto-discovers workspace by walking up looking for `tools/verdandi/` |

### structures/ -- Frozen Pydantic Data Models (zero methods, `ConfigDict(frozen=True)`)

| File | Purpose | Key Classes |
|------|---------|-------------|
| `structures/fields.py` | Tier 1 field models and ref type aliases | `Pattern` (regex + description), `Atom` (type + pattern + excludes), `Enum` (values), `Element` (inherits atom/enum + format), `Union_` (oneOf composition). Ref aliases: `PatternRef`, `AtomOrEnumRef`, `UnionMemberRef`, `FieldRef` |
| `structures/simple_containers.py` | Tier 2 simple container models | `Tuple_` (fixed-length typed sequence), `Simplearray` (variable-length single-type array), `Simplegroup` (flat object with required/optional/conditional zones), `SimplegroupConditionalEntry`. Ref alias: `SimplegroupItemRef` |
| `structures/complex_containers.py` | Tier 3 complex container models | `Array` (array of simplegroups), `ArrayOneOf` (oneOf for array items), `Group` (object with fields + containers sections), `GroupFields`, `GroupContainers`, `GroupFieldConditionalEntry`, `GroupContainerConditionalEntry`, `Superarray` (array of groups/simplegroups), `SuperarrayOneOf`. Ref aliases: `SimplegroupRef`, `GroupContainerRef`, `GroupFieldConditionalRef`, `GroupOrSimplegroupRef` |
| `structures/conditionals.py` | Conditional presence predicates | `ConditionalWhen` (field + equals/in predicate for only_when/always_when/not_when blocks) |
| `structures/top_level.py` | Tier 4 top-level and root models | `Section` (components are complex containers only), `Shallowsection` (fields + limited containers, max 2), `ShallowContainers`, `ShallowFieldConditionalEntry`, `Schema` (root: references sections and/or shallowsections, nullable support). Ref aliases: `ComplexContainerRef`, `ShallowContainerRef`, `ShallowFieldConditionalRef`, `SectionOnlyRef`, `ShallowsectionOnlyRef` |
| `structures/levels.py` | Level enum -- load order IS declaration order | `Level` enum: pattern, enum, atom, element, union, tuple, simplearray, simplegroup, array, group, superarray, section, shallowsection, schema. Each member's value is the Pydantic model class for that level. |
| `structures/schema_output.py` | JSON Schema output models | `SchemaDocument` (root), `SchemaObject` (groups/sections), `SchemaField` (leaf properties), `SchemaArray`, `SchemaTupleArray`, `SchemaOneOfField` (union fields), `SchemaOneOf` (polymorphic array items), `SchemaRef` ($ref pointer), `SchemaConditional`/`SchemaCondition` (if/then/else), `SchemaRootConditional`/`SchemaNestedPath` (cross-section conditionals), `SchemaNullableObject`/`SchemaNullType` (nullable wrapping), `SchemaConst`, `SchemaEnumConstraint`, `ValidationConstraint`, `SchemaNotBlock`, `SchemaSemanticExt`, `SchemaConstraintBlock` |

### functions/pure/ -- No IO, No Side Effects

| File | Purpose | Key Functions |
|------|---------|---------------|
| `functions/pure/pydantic_validators.py` | Shared ref conversion for Verdandi YAML references | `ref_from_cache(value, info)` -- BeforeValidator that converts string refs like `"atom/kebab_string"` to cached Pydantic models during model_validate(). Pass-through for models handles test cases. |
| `functions/pure/build_fields.py` | Field-level and simple container builders (always inlined, never $defs candidates) | `build_atom()`, `build_enum()`, `build_element()`, `build_union()`, `build_field()` (dispatch by type), `build_tuple()`, `build_simplearray()`, `build_simple()` (dispatch for fields + simple containers), `build_simplegroup()`, `build_if_condition()`, `build_conditional_entry()` |
| `functions/pure/build_containers.py` | Complex container and top-level builders with $defs tracking | `build_or_ref()` (build inline or emit $ref for shared models), `build_model()` (dispatch any Verdandi model), `build_array()`, `build_superarray()`, `build_group_properties()`, `build_group()`, `build_section()`, `build_shallowsection()`, `defs_key()` (cache key to $defs key conversion) |
| `functions/pure/exporter.py` | Tree walk, shared node detection, SchemaDocument assembly | `reverse_cache_index()` (id(model) -> cache_key mapping), `iter_child_models()` (generic Pydantic field iteration), `count_refs()` (iterative tree walk counting occurrences for $defs detection), `shared_keys()` (frozenset of keys appearing 2+ times), `build_schema_properties()` (top-level properties with nullable wrapping), `export_schema()` (complete SchemaDocument assembly), `export_all_schemas()` (batch export) |

### functions/impure/ -- File IO (exactly 2 impure files + orchestrator)

| File | Purpose | Key Functions |
|------|---------|---------------|
| `functions/impure/loader.py` | Supply-driven YAML loader (the ONLY file reader) | `load_file()` (load single YAML into cache via level's model_validate), `try_load_file()` (error-catching wrapper), `load_all_levels()` (iterate Level enum in order, glob each directory, populate cache bottom-up) |
| `functions/impure/writer.py` | JSON serialization + file writing + HTML sidecar generation (the ONLY file writer) | `serialize_schema()` (model_dump_json called here and NOWHERE ELSE), `write_schema()` (write JSON to disk), `load_inspect_schema()` (dynamic import of tools/inspect_schema.py), `write_sidecar()` (generate HTML sidecar) |
| `functions/impure/pipeline.py` | Orchestration: load, export, write | `resolve_paths()` (verdandi + output directory resolution), `schema_filename()` (cache key to output filename), `run_all()` (default: load + export + write all schemas + sidecars), `run_check()` (drift detection without writing), `run_list()` (print available schemas) |

---

## 8. Context Refresh Guide

For an LLM mid-session that needs to refresh specific understanding.

| If You Need To Understand... | Read This |
|------------------------------|-----------|
| The loading pipeline (supply-driven, level-ordered, BeforeValidator ref conversion) | `tools/draupnir/QUICKSTART.md` "The Loading Pipeline" section; or `context/draupnir.md` "Phase 1: Loading" |
| The export pipeline ($defs detection, tree walk, SchemaDocument assembly) | `context/draupnir.md` "Phase 2: Exporting"; source: `functions/pure/exporter.py` |
| The Verdandi hierarchy as draupnir sees it (15 levels, 4 tiers, tier containment) | `context/draupnir.md` "Verdandi Composition Hierarchy" tables; `tools/verdandi/COMPOSITION_RULES.md` |
| Pure/impure separation (why IO is in exactly 2 files) | `tools/draupnir/CLAUDE.md` "IO Externalization" section; `tools/draupnir/QUICKSTART.md` "Two-Boundary IO Design" |
| Design rationale and history (why the rebuild happened, what changed) | `tools/draupnir/DRAUPNIR_REDESIGN.md` sections 1-6; `documentation/toolcompose/WHY_SCHEMA_COMPOSITION_IS_THE_KEY.md` |
| Anti-patterns and failure modes (what NOT to do) | `tools/draupnir/CLAUDE.md` "You Will Get These Things Wrong" (13 items); `tools/draupnir/QUICKSTART.md` "What NOT to Do" |
| How draupnir fits in the end-to-end pipeline (schema generation -> nornir -> transform) | `definitions/TOOL_BUILDING.md` section "Stage 0: Schema Generation"; `context/draupnir.md` "Relationship to Other Tools" |
| Design decisions D1-D11 (requirement model, capability model, security, dispatch) | `context/draupnir.md` "From CRITICAL_DECISIONS.md" enrichment section; source: `documentation/pipeline/CRITICAL_DECISIONS.md` |
| Ref type aliases and tier enforcement (how typed unions enforce hierarchy) | `context/draupnir.md` "Ref Type Aliases"; source: each `structures/*.py` module's type alias definitions |
| The $defs/$ref mechanism (shared node detection, $defs population) | `context/draupnir.md` "The $defs/$ref mechanism"; source: `functions/pure/build_containers.py` `build_or_ref()` |
| Schema output models (what JSON Schema shapes are produced) | Source: `structures/schema_output.py` (SchemaDocument, SchemaObject, SchemaField, etc.) |
| Gleipnir constraints and guardrail discipline | `tools/draupnir/CLAUDE.md` "Gleipnir" section and "Gleipnir as Diagnostic: Redirect vs Blocker" |
| LLM mistake patterns specific to this codebase | `documentation/toolcompose/SCHEMA_COMPOSITION_EXPLAINED_BY_LLM_FOR_LLM.md` (5 documented mistakes with corrections) |

---

## 9. Known Issues / Active Work

### From Discrepancy Alerts (`context/discrepancy_ALERT_draupnir.md`)

**ALERT 1: `tools/agent_schema.py` still exists on disk.** The 1710-line predecessor file is described as "replaced by draupnir" in multiple documents but has not been deleted or marked as deprecated. It has a working PEP 723 shebang and could be executed. Resolution: ask user whether intentional retention or overlooked deletion.

**ALERT 2: Quick Reference table uses old level names.** The "Quick Reference: When to Do What" table in `documentation/toolcompose/SCHEMA_COMPOSITION_EXPLAINED_BY_LLM_FOR_LLM.md` maps actions to old directory names (`primitives/`, `composed/`, `supergroups/`, `superarrays/`) instead of current Verdandi names. An LLM following it literally would target non-existent directories. The document header has been annotated, but the table itself remains stale.

**ALERT 3: CRITICAL_DECISIONS.md D3 references "8-level hierarchy".** The D3 design decision (mandatory propagation, fail-and-report) still says "build schema from 8-level hierarchy" when draupnir now loads 15 levels. The principle is correct regardless of level count; the reference is historically accurate but factually stale.

### From Reconciliation Log (2026-02-26)

Seven documentation files were consulted during reconciliation:
- 7 enrichments added to `context/draupnir.md` (one per source document)
- 7 stale documentation items fixed (level counts updated, architecture descriptions rewritten)
- All fixes are noted in the reconciliation log at the bottom of `context/draupnir.md`

**ALERT 4: test_pipeline.py assertions are stale.** `EXPECTED_SCHEMA_COUNT = 12` but actual schema count is 13 (agent-anthropic-render added). The expected levels set in `test_all_levels_represented` is missing `"field"`. Both tests currently FAIL. See `context/discrepancy_ALERT_draupnir.md`.

### Pipeline Status

Per `documentation/pipeline/CRITICAL_DECISIONS.md`: 12 of 13 next-step items completed. Item 12 ("Update existing agent definition JSON files for new schema structure") remains open. Item 13 (resolver/generator integration) is in progress with the full nornir-gated pipeline.
