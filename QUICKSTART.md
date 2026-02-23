# Draupnir Quickstart

## What It Is

Draupnir is a schema generator that walks YAML composition trees and produces JSON Schema files. It reads from an 8-level YAML hierarchy (primitives, composed, groups, arrays, supergroups, superarrays, sections, schemas) and outputs JSON Schema Draft 2020-12 files used to validate agent definitions in the bragi pipeline.

It replaces the monolithic `tools/agent_schema.py` with a functional architecture: frozen Pydantic models, pure functions, IO at boundaries only.

The pipeline flows: **YAML source** (`standards/toolcompose/`) -> **draupnir** -> **JSON Schema** (`schemas/`) -> **nornir** (downstream validator).

## How to Use It

### Generate all schemas

```bash
/Users/johnny/.ai/spaces/bragi/tools/draupnir/.venv/bin/draupnir --all
```

### Generate one schema

```bash
/Users/johnny/.ai/spaces/bragi/tools/draupnir/.venv/bin/draupnir agent-raw-definition
```

### Check for drift (no writes)

```bash
/Users/johnny/.ai/spaces/bragi/tools/draupnir/.venv/bin/draupnir --all --check
```

Exit code 0 = no drift. Exit code 1 = drift detected or schemas missing.

### List available schemas

```bash
/Users/johnny/.ai/spaces/bragi/tools/draupnir/.venv/bin/draupnir --list
```

### Override directories

```bash
/Users/johnny/.ai/spaces/bragi/tools/draupnir/.venv/bin/draupnir --all \
  --standards-dir /path/to/toolcompose \
  --output-dir /path/to/output
```

### Run tests

```bash
cd /Users/johnny/.ai/spaces/bragi/tools/draupnir && uv run pytest tests/
```

### Default paths

- Input YAML: `/Users/johnny/.ai/spaces/bragi/standards/toolcompose/`
- Output schemas: `/Users/johnny/.ai/spaces/bragi/schemas/`
- HTML sidecars: Same directory as schemas, with `.html` appended to the `.schema.json` filename

## Pipeline Architecture

```
loaders.py          walkers.py           resolvers.py         builders.py          writers.py
[YAML files] ──→ [Raw models] ──→ [Walked models] ──→ [Resolved models] ──→ [Schema models] ──→ [JSON files]
   (IO)            (pure+IO)            (pure)               (pure)              (IO)
```

Six internal stages:

1. **Load primitives pool** -- All primitives + thin composed type-adopters indexed by name
2. **Load schema root** -- Parse the schema YAML (e.g., `schema/agent-raw-definition.yaml`)
3. **Bridge sections** -- Map section names to file paths if not already explicit
4. **Walk tree** -- Follow file references from schema -> sections -> groups -> composed/arrays
5. **Resolve** -- Walk primitive type chains, accumulate properties, produce `ResolvedSchema`
6. **Build** -- Convert `ResolvedSchema` to `SchemaDocument` (JSON Schema output models)

Serialization (`model_dump()`) happens once at the writer boundary.

## What NOT to Do

### The 5 Mistakes LLMs Always Make

These are documented from actual sessions where LLMs fought the architecture. You will want to make all of them:

1. **"Just delete the intermediate levels"** -- You will see supergroup -> array -> group chains and think the array level is unnecessary. It is not. Arrays hold polymorphism (oneOf). Removing the array level loses the ability to have polymorphic items. When you see a level being bypassed, fix the routing -- do not delete the level.

2. **Prescribing fixes instead of asking** -- You will find hierarchy violations and immediately declare the fix. You can be right about the violation and completely wrong about the fix. Present findings, ask what the architect wants.

3. **Adding phantom levels for purity** -- When you find pragmatic exceptions (primitives referencing siblings, primitives referencing PATH_BLOCKLIST), do not suggest creating `ur-primitives/` and `ur-composed/` levels. Three documented exceptions cost less than two additional directory levels.

4. **Confusing composition with flattening** -- Type adoption is NOT "turning things into strings." When `include_instruction.yaml` says `fields: {include: path_exists_any}`, it creates a typed object with a validated field. The primitive carries constraints (blocklist + existence check). The composed type carries object structure.

5. **Creating single-consumer files** -- Each decomposed file must justify its existence through reuse. A file consumed by exactly one parent is fragmentation, not composition. The criteria include bug (YAML files that existed but were never wired in) happened because decomposition was too deep.

### Never glob directories

The walker follows references from the schema root. Never use `Path.glob("**/*.yaml")` to discover files. The tree tells you what to load.

### Never put IO in pure functions

Files under `functions/pure/` must not read files, write files, print, or access environment variables. If a pure function needs data from a file, the caller reads the file and passes the data in.

### Never add methods to structures

`structures.py` contains frozen Pydantic models with ZERO logic -- no methods, no `@property`, no classmethods. All logic belongs in `functions/pure/` or `functions/impure/`.

### Never return dicts from pipeline functions

Every intermediate value is a typed Pydantic model. No `dict[str, Any]`. No `JsonDict`. Create a model in `structures.py` if you need a new shape.

### Never use `Any` types

The data is always typed. Loaders validate YAML into Pydantic models immediately. There is no untyped data in the system.

### Never change `name:` fields between stages

The `name:` field in YAML is the stable JSON field name. It never changes per pipeline stage. The filename carries the variant (e.g., `security_resolved.yaml` still has `name: security`). This is the core problem draupnir was built to solve.

### Never use name-based lookups for non-primitives

File-based structural references (field name -> file path) are used at ALL levels above primitives. Name-based type adoption is used ONLY for primitives.

### Never add fallback logic to the generator

Fallback logic papers over hierarchy violations. When supergroups could fall back to referencing groups directly (bypassing arrays), it meant the hierarchy was not enforced. Removing fallback logic exposed the violations, which were then fixed. Strict enforcement catches bugs. Fallbacks hide them.

### Never import sideways or upward

The import direction rule: import from any level below you, never from the same level or above. Documented pragmatic exceptions exist (PATH_BLOCKLIST, path_exists_* siblings). New exceptions require the same justification.

### Never hardcode requirement on shared primitives

Shared primitives (referenced by multiple consumers in different contexts) MUST use `requirement: inherit`. This defers to the group composition context. Hardcoding `optional` defeats AllOf composition. Hardcoding `required` forces it everywhere.

### Never exceed Gleipnir constraints

- Max 50 lines per function
- Max 5 parameters per function
- Max 4 nesting depth
- Max 4 quarantined (IO) files

### Never skip reading the plan before modifying code

The design plan is at `~/.claude/plans/warm-gliding-kitten.md`. Before starting any phase of work, re-read the relevant section. Post-compaction summaries lose critical details.

## Where to Get Context

### Architecture and design

| Document | Path | Priority |
|---|---|---|
| Design plan (source of truth) | `~/.claude/plans/warm-gliding-kitten.md` | Read first |
| CLAUDE.md (anti-pattern warnings) | `/Users/johnny/.ai/spaces/bragi/tools/draupnir/CLAUDE.md` | Read first |
| Composition hierarchy explained (5 LLM mistakes) | `/Users/johnny/.ai/spaces/bragi/documentation/toolcompose/SCHEMA_COMPOSITION_EXPLAINED_BY_LLM_FOR_LLM.md` | Read if confused about hierarchy |
| Why schema composition is the key | `/Users/johnny/.ai/spaces/bragi/documentation/toolcompose/WHY_SCHEMA_COMPOSITION_IS_THE_KEY.md` | Read for lifecycle stage understanding |
| Full field tree with types | `/Users/johnny/.ai/spaces/bragi/documentation/pipeline/DEFINITION_FORMAT.md` | Visual reference |
| Critical design decisions (D1-D10) | `/Users/johnny/.ai/spaces/bragi/documentation/pipeline/CRITICAL_DECISIONS.md` | Authoritative decisions |
| Permissions calculation (AUTHORITATIVE) | `/Users/johnny/.ai/spaces/bragi/documentation/pipeline/PERMISSIONS_CALCULATION_REVISED.md` | Read if touching security/enforcement |
| Design reasoning (3-layer constraints, security) | `/Users/johnny/.ai/spaces/bragi/documentation/toolcompose/TOOL_COMPOSE_REASONING.md` | Read for WHY behind decisions |
| Context loss recovery | `/Users/johnny/.ai/spaces/bragi/documentation/behavioral/REFRESH.md` | Read after compaction or when uncertain |

### Source code

| Module | Path | Purpose |
|---|---|---|
| structures.py | `tools/draupnir/src/draupnir/structures.py` | All Pydantic models (Raw, Walked, Resolved, Schema output) |
| loaders.py | `tools/draupnir/src/draupnir/functions/impure/loaders.py` | YAML reading, Pydantic validation, SchemaLoaders factory |
| walkers.py | `tools/draupnir/src/draupnir/functions/pure/walkers.py` | Tree walking from schema root to composed fields |
| resolvers.py | `tools/draupnir/src/draupnir/functions/pure/resolvers.py` | Type chain resolution, walked-to-resolved conversion |
| builders.py | `tools/draupnir/src/draupnir/functions/pure/builders.py` | Resolved models to JSON Schema output models |
| stabilizers.py | `tools/draupnir/src/draupnir/functions/pure/stabilizers.py` | Stage suffix stripping |
| pipeline.py | `tools/draupnir/src/draupnir/functions/impure/pipeline.py` | Stage composition (orchestrator) |
| writers.py | `tools/draupnir/src/draupnir/functions/impure/writers.py` | JSON serialization, HTML sidecar generation |
| commands.py | `tools/draupnir/src/draupnir/functions/impure/commands.py` | CLI command implementations |
| cli.py | `tools/draupnir/src/draupnir/cli.py` | Argument parsing and dispatch |

### Input data

| Directory | Purpose |
|---|---|
| `standards/toolcompose/schema/` | Root schema definitions (12 YAML files) |
| `standards/toolcompose/sections/` | Section definitions |
| `standards/toolcompose/groups/` | Group definitions |
| `standards/toolcompose/composed/` | Composed field definitions |
| `standards/toolcompose/primitives/` | Primitive type definitions |
| `standards/toolcompose/arrays/` | Array definitions |
| `standards/toolcompose/supergroups/` | Supergroup definitions |
| `standards/toolcompose/superarrays/` | Superarray definitions |

### Output

| Directory | Purpose |
|---|---|
| `schemas/agent-*.schema.json` | Generated JSON Schema files (12) |
| `schemas/agent-*.schema.json.html` | HTML sidecar inspection files (12) |

### Gleipnir rules

| File | Purpose |
|---|---|
| `tools/draupnir/.gleipnir/rules.toml` | Suite-wide thresholds |
| `tools/draupnir/src/draupnir/.gleipnir/exceptions.toml` | Per-file exceptions (currently empty) |

### Related tools

| Tool | Purpose |
|---|---|
| `tools/agent_schema.py` | Predecessor monolith (still present, being replaced) |
| `tools/inspect_schema.py` | HTML sidecar generator (called by draupnir's writers) |
| `tools/nornir/` | Downstream Rust validator/writer that consumes draupnir output |
