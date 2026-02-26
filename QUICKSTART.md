# Draupnir -- Quickstart

## What It Does

Draupnir is a schema generator. It reads Verdandi YAML composition files from `tools/verdandi/` (14 level directories, ~178 files) and produces JSON Schema documents in `schemas/` (currently 12 schemas). It also generates HTML sidecar visualizations via `tools/inspect_schema.py`.

---

## How to Run

```bash
# Generate all schemas + HTML sidecars (default mode)
draupnir

# Check for drift without writing (exit 1 if any schema drifted)
draupnir --check

# List available schema filenames
draupnir --list

# Override directories
draupnir --verdandi-dir /path/to/verdandi --output-dir /path/to/output --workspace /path/to/root
```

The CLI auto-discovers the workspace root by walking up from its location looking for `tools/verdandi/`.

**Entry point:** defined in `pyproject.toml` as `draupnir = "draupnir.cli:main"`.

**Running tests:**
```bash
cd tools/draupnir
uv run pytest tests/
uv run pytest tests/test_guardrails.py   # Gleipnir structural checks -- run FREQUENTLY
```

---

## Input / Output

**Reads:**
- `tools/verdandi/{level}/*.yaml` -- 14 directories (pattern, enum, atom, element, union, tuple, simplearray, simplegroup, array, group, superarray, section, shallowsection, schema)
- Each YAML file is validated into a frozen Pydantic model specific to its level

**Produces:**
- `schemas/*.schema.json` -- JSON Schema documents (Draft 2020-12)
- `schemas/*.schema.json.html` -- HTML visualization sidecars (via inspect_schema.py)

**Currently generates 12 schemas**, including:
- `agent-raw-definition.schema.json`
- `agent-universal-format.schema.json`
- `agent-universal-render.schema.json`
- And 9 others for intermediate pipeline stages

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
                                   |
IMPURE: writer.py  --writes-->  JSON Schema files + HTML sidecars
```

### Source Layout

```
src/draupnir/
  cli.py                         # CLI: parse args, dispatch to pipeline
  structures/                    # Frozen Pydantic models (data only, zero methods)
    fields.py                    # Pattern, Atom, Enum, Element, Union_
    simple_containers.py         # Tuple_, Simplearray, Simplegroup
    complex_containers.py        # Array, Group, Superarray
    conditionals.py              # ConditionalWhen
    top_level.py                 # Section, Shallowsection, Schema
    levels.py                    # Level enum (load order = declaration order)
    schema_output.py             # JSON Schema output models
  functions/
    pure/                        # No side effects
      pydantic_validators.py     # ref_from_cache (string -> cached model)
      build_fields.py            # Field/simple container -> JSON Schema
      build_containers.py        # Complex container/section -> JSON Schema + $defs
      exporter.py                # Tree walk, shared detection, SchemaDocument assembly
    impure/                      # File IO only
      loader.py                  # Supply-driven YAML loader
      writer.py                  # JSON serialization + HTML sidecar
      pipeline.py                # Orchestration (run_all, run_check, run_list)
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
5. Assemble `SchemaDocument` per schema-level entry in the cache

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

**DO NOT write functions over 50 lines.** Gleipnir enforces this. Decompose.

**DO NOT use `Any` anywhere.** Every value has a known type.

**DO NOT re-export from `__init__.py`.** Always empty. Direct imports: `from draupnir.structures.fields import Pattern`.

**DO NOT use leading underscore names.** No `_private` functions. FP style: every function is a public composable unit.

**DO NOT call the directory `models/`.** The convention is `structures/`.

---

## Where to Get Required Context

| Resource | Location | Purpose |
|----------|----------|---------|
| **CLAUDE.md** | `tools/draupnir/CLAUDE.md` | Anti-patterns, recovery sources, Gleipnir discipline, context refresh protocol |
| **Design Doc** | `tools/draupnir/DRAUPNIR_REDESIGN.md` | Full architecture (~57K): models, loading, export, $defs, gated plan, anti-patterns |
| **Verdandi YAML** | `tools/verdandi/` | The actual input files (14 level directories) |
| **Composition Rules** | `tools/verdandi/COMPOSITION_RULES.md` | Hierarchy spec, tier containment rules |
| **Gleipnir Rules** | `tools/draupnir/.gleipnir/rules.toml` (inherited) | Structural constraints (50-line functions, 5 params, etc.) |
| **Schema Output** | `schemas/*.schema.json` | The produced JSON Schema files |
| **inspect_schema.py** | `tools/inspect_schema.py` | HTML sidecar generator called by writer |
| **nornir** | `tools/nornir/` | Rust validation tool consuming the schemas |

---

## Verdandi Hierarchy (What Draupnir Consumes)

```
Tier 1 - Fields:           pattern -> atom -> enum -> element -> union
Tier 2 - Simple Containers: tuple, simplearray, simplegroup
Tier 3 - Complex Containers: array, group, superarray
Tier 4 - Top Level:         section, shallowsection, schema
```

Load order = bottom to top. References only point downward (a group can reference an array, but an array cannot reference a group). This is enforced by the typed ref aliases on each model.

---

## Key Invariants

1. **Load order is declaration order** -- the `Level` enum in `levels.py` defines it
2. **Models hold models** -- not strings, not dicts, not IDs
3. **Cache key format** -- `"level_name/file_stem"` (e.g., `"atom/kebab_string"`)
4. **$defs key format** -- `"level__name"` (slash replaced with double underscore)
5. **Output filename format** -- `"name.schema.json"` (schema key without the "schema/" prefix)
6. **All models are frozen** -- `ConfigDict(frozen=True)` on every model
7. **12 schemas currently expected** -- `EXPECTED_SCHEMA_COUNT = 12` in test_pipeline.py
