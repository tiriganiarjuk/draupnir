# Draupnir QUICKSTART

Draupnir is a schema generator. It reads Verdandi YAML composition files from `tools/verdandi/` (15 level directories, ~348 files) and produces JSON Schema documents in `schemas/` (13 pipeline-stage schemas + 7 include-fragment schemas) plus HTML sidecar visualizations.

---

## How to Run

```bash
# From the draupnir tool directory
cd /Users/johnny/.ai/spaces/bragi/tools/draupnir

# Generate all schemas + HTML sidecars (default mode)
uv run draupnir --all

# Check for drift without writing (exit 1 if any schema drifted)
uv run draupnir --check

# List available schema filenames
uv run draupnir --list

# Generate standalone include-fragment schemas
uv run draupnir --fragments

# Override directories
uv run draupnir --verdandi-dir /path/to/verdandi --output-dir /path/to/output --workspace /path/to/root
```

The CLI auto-discovers the workspace root by walking up from its location looking for `tools/verdandi/`.

**Entry point:** defined in `pyproject.toml` as `draupnir = "draupnir.cli:main"`.

**Running tests:**
```bash
cd /Users/johnny/.ai/spaces/bragi/tools/draupnir
uv run pytest tests/
uv run pytest tests/test_guardrails.py   # Gleipnir structural checks -- run FREQUENTLY
```

---

## Input / Output

**Reads:**
- `tools/verdandi/{level}/*.yaml` -- 15 directories (pattern, enum, atom, element, union, tuple, field, simplearray, simplegroup, array, group, superarray, section, shallowsection, schema)
- Each YAML file is validated into a frozen Pydantic model specific to its level

**Produces:**
- `schemas/agent-*.schema.json` -- 13 pipeline-stage JSON Schema documents (Draft 2020-12)
- `schemas/include-*.schema.json` -- 7 include-fragment schemas
- `schemas/*.schema.json.html` -- HTML visualization sidecars (via inspect_schema.py)

**Pipeline-stage schemas include:**
- `agent-raw-definition.schema.json` (entry point)
- `agent-paths-resolved.schema.json`, `agent-permissions-resolved.schema.json`
- `agent-instructions-reduced.schema.json`, `agent-examples-reduced.schema.json`
- `agent-guardrails-reduced.schema.json`, `agent-criteria-merged.schema.json`
- `agent-execution-merged.schema.json`, `agent-universal-format.schema.json`
- `agent-universal-render.schema.json`, and others

**Fragment schemas include:**
- `include-success-criteria.schema.json`, `include-failure-criteria.schema.json`
- `include-execution-instructions.schema.json`, `include-example-entries.schema.json`
- `include-example-group.schema.json`, `include-guardrails-constraints.schema.json`
- `include-guardrails-anti-patterns.schema.json`

---

## Architecture Overview

### Two-Boundary IO Design

IO exists in exactly two files. Everything else is pure computation.

```
IMPURE: loader.py  --reads-->  Verdandi YAML
                                   |
                              cache (dict of frozen Pydantic models)
                                   |
PURE:  exporter.py  --walks-->  model tree
       build_fields.py          |
       build_containers.py      SchemaDocument models
       build_cross_section.py   |
                                   |
IMPURE: writer.py  --writes-->  JSON Schema files + HTML sidecars
```

### Source Layout

```
src/draupnir/
  cli.py                         # CLI: parse args, dispatch to pipeline
  structures/                    # Frozen Pydantic models (data only, zero methods)
    conditionals.py              # ConditionalWhen predicate
    field.py                     # SemanticBlock, ConstraintRule sub-models
    fields.py                    # Pattern, Atom, Enum, Element, Union_ (Tier 1)
    simple_containers.py         # Tuple_, VerdandiField, Simplearray, Simplegroup (Tier 2)
    complex_containers.py        # Array, Group, Superarray + OneOf variants (Tier 3)
    top_level.py                 # Section, Shallowsection, Schema (Tier 4)
    levels.py                    # Level enum (load order = declaration order)
    schema_output.py             # JSON Schema output models (SchemaDocument, etc.)
  functions/
    pure/                        # No side effects
      pydantic_validators.py     # ref_from_cache (string -> cached model)
      build_fields.py            # Field/simple container -> JSON Schema
      build_containers.py        # Complex container/section -> JSON Schema + $defs
      build_cross_section.py     # Cross-section conditional -> root allOf entries
      exporter.py                # Tree walk, shared detection, SchemaDocument assembly
    impure/                      # File IO only
      loader.py                  # Supply-driven YAML loader (ONLY file reader)
      writer.py                  # JSON serialization + HTML sidecar (ONLY file writer)
      pipeline.py                # Orchestration (run_all, run_check, run_list, run_fragments)
```

### The Loading Pipeline

1. Iterate `Level` enum in declaration order (pattern first, schema last)
2. Glob `verdandi_root/{level_name}/*.yaml` for each level
3. Validate each YAML file through its level's Pydantic model
4. `BeforeValidator(ref_from_cache)` on ref fields converts string refs (e.g., `"atom/kebab_string"`) to actual cached models
5. Lower levels load first, guaranteeing refs are in cache when higher levels validate

After loading, the cache holds the entire tree as frozen models that hold their children as actual model instances (not strings, not dicts).

### The Export Pipeline

1. Build reverse index: `id(model) -> cache_key`
2. Walk model tree counting ref occurrences; keys with count >= 2 are shared
3. Build JSON Schema output models from the Verdandi input models
4. Shared models go to `$defs`; subsequent refs become `$ref` pointers
5. Cross-section conditionals (dotted field paths) are hoisted to root `allOf`
6. Assemble `SchemaDocument` per schema-level entry in the cache

### The Fragment Pipeline

1. Same loading as above (full cache)
2. Look up specific cache keys from `FRAGMENT_REGISTRY` in pipeline.py
3. Build each as a standalone schema via `export_fragment()`
4. Array fragments are wrapped in `{"items": ...}` object (TOML root must be a table)
5. Write with `$schema`/`$id` metadata added at serialization boundary

---

## What NOT to Do

These are documented failure modes from previous sessions. Each has caused significant rework.

**DO NOT create a "resolve" function or step.** There is no resolution phase. Loading IS the pipeline. Pydantic BeforeValidator converts string refs to cached models during model_validate(). Every model is in final form from the moment it validates.

**DO NOT create Raw/Resolved model pairs.** One model per level. No RawPattern/ResolvedPattern. A Pattern is a Pattern. An Atom that holds a Pattern holds the actual frozen model instance.

**DO NOT put IO outside loader.py and writer.py.** No `Path.read_text()` in the builder. No `open()` in the exporter. Two impure files only.

**DO NOT use AfterValidator for ref types.** BeforeValidator fires first (string -> model), then union type check fires. AfterValidator would operate on the wrong type.

**DO NOT build demand-driven recursive loading.** The architecture is supply-driven. Glob levels in order. When BeforeValidator fires, the referenced model is guaranteed in cache. Missing ref = hard error (file not found), not a recursive load trigger.

**DO NOT reach for dict.** This is a canary for lost architecture. Every YAML shape is known and has a typed model. Pydantic union matching handles polymorphism. `model_dump()` happens ONCE at the writer boundary.

**DO NOT add methods to models.** Structures are frozen data containers. Zero methods. Logic lives in `functions/`.

**DO NOT write long functions.** Each function does one thing. If it's growing, decompose. Gleipnir enforces this structurally.

**DO NOT use `Any` anywhere.** Every value has a known type.

**DO NOT re-export from `__init__.py`.** Always empty. Direct imports: `from draupnir.structures.fields import Pattern`.

**DO NOT use leading underscore names.** No `_private` functions. FP style: every function is a public composable unit.

**DO NOT call the directory `models/`.** The convention is `structures/`.

---

## Where to Get Required Context

| Resource | Location | Purpose |
|----------|----------|---------|
| **CLAUDE.md** | `tools/draupnir/CLAUDE.md` | Anti-patterns (13 failure modes), recovery sources, Gleipnir discipline, context refresh protocol |
| **CONTEXT_MAP.md** | `tools/draupnir/CONTEXT_MAP.md` | Source code map, upstream/downstream deps, where knowledge lives |
| **Context Summary** | `context/draupnir.md` | Architecture overview, pipeline phases, tier hierarchy, ref type system, design decisions |
| **Design Doc** | `tools/draupnir/DRAUPNIR_REDESIGN.md` | Full architecture (~57K): models, loading, export, $defs, gated plan, anti-patterns |
| **Composition Rules** | `tools/verdandi/COMPOSITION_RULES.md` | Hierarchy spec, tier containment rules |
| **Gleipnir Rules** | `tools/draupnir/.gleipnir/rules.toml` | Structural constraints enforced at runtime |

---

## Verdandi Hierarchy (What Draupnir Consumes)

```
Tier 1 - Fields:            pattern, enum, atom, element, union
Tier 2 - Simple Containers: tuple, field (VerdandiField), simplearray, simplegroup
Tier 3 - Complex Containers: array, group, superarray
Tier 4 - Top Level:          section, shallowsection, schema
```

Load order = bottom to top (Level enum declaration order). References only point downward (a group can reference an array, but an array cannot reference a group). This is enforced by typed ref aliases on each model with union type constraints.

---

## Downstream: After Schema Generation

After draupnir regenerates schemas:

1. **Deploy nornir gates + CLI checkers** to embed updated schemas: `cd tools/nornir && ./deploy_gates.py`
2. **transform_to_universal** auto-generates Pydantic models from the new schemas
3. **inspect_schema.py** reads the generated schemas for HTML visualization (called automatically during `--all`)
4. **scaffold_definition.py** reads `agent-raw-definition.schema.json` for TOML scaffolding

`deploy_gates.py` builds CLI binaries with cargo, builds gate modules with maturin, extracts `.so` files, creates symlinks, and verifies. Do NOT use bare `cargo build` — it skips gate deployment.

---

## Key Invariants

1. **Load order is declaration order** -- the `Level` enum in `levels.py` defines it
2. **Models hold models** -- not strings, not dicts, not IDs
3. **Cache key format** -- `"level_name/file_stem"` (e.g., `"atom/kebab_string"`)
4. **$defs key format** -- `"level__name"` (slash replaced with double underscore)
5. **Output filename format** -- `"name.schema.json"` (schema key without the `"schema/"` prefix)
6. **All models are frozen** -- `ConfigDict(frozen=True)` on every model
7. **13 pipeline schemas + 7 fragment schemas** -- from 13 Verdandi `schema/*.yaml` root definitions
8. **Serialization happens once** -- `model_dump_json(by_alias=True, exclude_none=True)` in writer.py only
