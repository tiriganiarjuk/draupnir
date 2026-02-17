# Draupnir — Context Refresh Protocol

## STOP. Read this before writing any code.

You are building a schema generator. You have a plan file. You probably feel like you understand the design well enough to start coding. **You are almost certainly wrong.**

After compaction, you have a summary of the design — not the design itself. Summaries preserve conclusions but lose the reasoning, the constraints, the specific shapes. You will produce code that looks right, compiles, and silently violates the architecture because the summary told you WHAT but not HOW or WHY NOT.

**This has happened before.** Previous LLM sessions in this workspace have:
- Implemented structured fields as `type: string` (silently dropping architecture)
- Flattened 8-level composition hierarchies because they "seemed redundant"
- Globbed entire directories when the design requires walking from root
- Put IO in pure functions because "it's just one file read"
- Built 50+ line monolith functions while claiming to follow Gleipnir rules
- Returned `dict[str, Any]` from builders because "it's JSON Schema, dicts are natural"
- Created an `unsafe/` directory for loaders that didn't need `Any` types at all
- Used `load_fn: Callable` without typed returns, tainting pure code with untyped data

None of them felt uncertain while doing it.

---

## The Plan File

**Location:** `~/.claude/plans/warm-gliding-kitten.md`

This is your source of truth for the build. Read it. Not skim it — read it. The plan contains:
- Architecture (the Phoenix pattern from `phoenix/cli/`)
- Design principles (7 non-negotiable rules)
- Structures progression (Raw → Walked → Resolved → Schema output — 4 stages, all typed)
- The walk algorithm (how the tree is traversed)
- YAML changes required (what gets modified in Phase 5)
- Build order (6 phases with dependencies)
- References per phase (what to re-read before starting each phase)

**Before starting ANY phase**, re-read that phase's section in the plan file. Check the references listed there.

---

## Design Decisions You Will Violate

These are the decisions most likely to be lost after compaction. If you can't explain WHY each one matters, re-read the plan.

### 1. Walk from root, not glob

The current `agent_schema.py` globs all YAML files into flat namespace maps. This creates collision risk between stage variants (e.g., `security.yaml` vs `security_resolved.yaml` both having fields called `security_paths`).

**Draupnir walks from the schema YAML outward.** The schema references sections. Sections reference groups/arrays. Groups reference composed fields. Composed fields reference primitives by name. Only load what the tree actually references.

If you find yourself writing `Path.glob("**/*.yaml")` or building a flat dict of all files — **STOP**. Re-read the plan's "Walk Algorithm" section.

### 2. Two reference models

There are exactly TWO ways things reference each other:

- **File-based structural references** — Used at ALL levels above primitives. The key is the JSON field name, the value is a relative file path. Example: `security_paths: groups/security_paths_resolved.yaml`
- **Name-based type adoption** — Used ONLY for primitives. A composed field's `type:` names a primitive. Example: `type: path_allowed_absolute`

If you find yourself using name-based lookups for anything other than primitives — **STOP**. Re-read the plan's "Two Reference Models" section.

### 3. Stable field names

The `name:` field in every YAML file = the JSON field name in the output schema. It NEVER changes per pipeline stage. The YAML **filename** carries the variant (`context_path.yaml` vs `context_path_resolved.yaml`), but both have `name: context_path`.

This is the entire reason Draupnir exists. The old generator forced field name changes per stage. If you find yourself changing `name:` values between stages — **STOP**. You are recreating the exact problem this rebuild fixes.

### 4. structures.py has ZERO logic

Frozen Pydantic models only. No methods. No `@property`. No `def resolve()`. No `def to_dict()`. No classmethod factories. Just fields with types and `model_config = ConfigDict(frozen=True)`.

**Reference:** `phoenix/cli/space_schema_gen/structures.py` — look at it. It's models and nothing else.

If you find yourself adding a method to a structure — **STOP**. That logic belongs in a function in `functions/pure/`.

### 5. Pure functions are actually pure

Functions in `functions/pure/` take data and return data. They do not:
- Read files (`Path.read_text()`, `open()`, `yaml.safe_load()`)
- Write files
- Print anything
- Access environment variables
- Mutate their arguments

If a pure function needs data from a file, the CALLER reads the file and passes the data in.

The walkers use `SchemaLoaders` — a frozen Pydantic model containing typed callable loaders. The walker logic is deterministic; the IO is injected via the loader callables constructed at the impure boundary.

**Reference:** `phoenix/coding_reference/AI_BREAKTHROUGHS_IO_EXTERNALIZATION.md`

### 6. Type safety all the way through — model_dump() only at the writer boundary

**This is the most important architectural discovery from Phase 3.**

Every stage of the pipeline passes typed Pydantic models:
- Loaders return `RawPrimitive`, `RawComposed`, `RawGroup`, etc. (not `dict`)
- Walkers return `WalkedSchema` containing `WalkedSection`, `WalkedGroup`, etc.
- Resolvers return `ResolvedSchema` containing `ResolvedSection`, `ResolvedGroup`, etc.
- Builders return `SchemaDocument` containing `SchemaObject`, `SchemaField`, etc.
- **Only the writer** calls `model_dump(by_alias=True, exclude_none=True)` to serialize to JSON

There are ZERO untyped dicts in the pipeline. No `dict[str, Any]`. No `JsonDict`. No "we'll serialize later." Every intermediate value has a frozen Pydantic model with named, typed fields.

If you find yourself returning a `dict` from any function — **STOP**. Create a typed Pydantic model in `structures.py` instead.

### 7. IO in exactly two places

- `functions/impure/loaders.py` — reads YAML files, validates into typed Pydantic models
- `functions/impure/writers.py` — serializes SchemaDocument via model_dump(), writes JSON files

That's it. No `unsafe/` directory — there is no untyped data in this system. The YAML structure is known at every call site. Pydantic validates immediately at the boundary. `Any` is never needed.

If you're about to put `Path` or `open()` anywhere else — **STOP**.

---

## The SchemaLoaders Pattern

The walker needs to load files (IO) but must remain pure (no IO). This is solved by dependency inversion:

```python
# In structures.py — the interface
class SchemaLoaders(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    composed: Callable[[PurePosixPath], RawComposed]
    group: Callable[[PurePosixPath], RawGroup]
    array: Callable[[PurePosixPath], RawArray]
    section: Callable[[PurePosixPath], RawSection]

# In functions/impure/loaders.py — the implementation
def make_schema_loaders(root: Path) -> SchemaLoaders:
    return SchemaLoaders(
        composed=lambda p: load_composed(root / p),
        group=lambda p: load_group(root / p),
        array=lambda p: load_array(root / p),
        section=lambda p: load_section(root / p),
    )

# In functions/pure/walkers.py — the consumer
def walk_group(raw_group: RawGroup, root: PurePosixPath, loaders: SchemaLoaders) -> WalkedGroup:
    # Uses loaders.composed(path), loaders.group(path), etc.
    # Pure: given same loaders, always produces same output
```

Pure code defines the interface (SchemaLoaders). Impure code implements it (make_schema_loaders). The walker receives it as a parameter. No imports cross the boundary.

---

## Gleipnir Constraints

These are enforced, not advisory:
- **Max 50 lines per function** — If you're at 40 and still going, decompose NOW
- **Max 5 parameters** — If you need 6, you need a structure
- **Max 4 nesting depth** — If you're inside `if` inside `for` inside `if` inside `for`, extract
- **Max 4 quarantined files** — IO-touching files are limited

**Reference:** `.gleipnir/rules.toml` in this project

---

## How to Actually Read (Not Perform Reading)

When you re-read a source document:

1. **Look for contradictions.** Find something that doesn't match what you're about to build. If everything matches, you're skimming.
2. **Look for specifics you can't recall.** Field types. Required vs optional. Which reference model is used where. If you remember everything, you're pattern-matching from the summary, not reading.
3. **State what you recovered.** Don't say "now I understand." Say: "The walker receives SchemaLoaders — a frozen Pydantic model with typed callables. Groups use file-based field references, not name-based. Arrays reference groups for their items via file path. Builders return SchemaDocument, not dicts."

Specifics prove understanding. "I understand" proves nothing.

---

## Source Documents to Re-Read When Uncertain

### Architecture & Design
| Document | Path | What it tells you |
|---|---|---|
| **The Plan** | `~/.claude/plans/warm-gliding-kitten.md` | Everything — architecture, structures, walk algorithm, build order |
| **SCHEMA_COMPOSITION_EXPLAINED** | `standards/SCHEMA_COMPOSITION_EXPLAINED_BY_LLM_FOR_LLM.md` | The 8-level hierarchy, why each level exists |
| **DEFINITION_FORMAT** | `standards/toolcompose/DEFINITION_FORMAT.md` | Full field tree with type annotations |
| **CRITICAL_DECISIONS** | `standards/toolcompose/CRITICAL_DECISIONS.md` | Decisions D1-D10, rationale |

### Functional Programming Discipline
| Document | Path | What it tells you |
|---|---|---|
| **Hemingway Coding** | `phoenix/coding_reference/AI_BREAKTHROUGHS_HEMINGWAY_CODING.md` | Each function does ONE thing |
| **IO Externalization** | `phoenix/coding_reference/AI_BREAKTHROUGHS_IO_EXTERNALIZATION.md` | Why IO lives at the boundary |
| **Safety Taxonomy** | `phoenix/coding_reference/AI_BREAKTHROUGHS_SAFETY_TAXONOMY.md` | pure/impure classification |
| **Economic Model** | `phoenix/coding_reference/AI_BREAKTHROUGHS_ECONOMIC_MODEL.md` | Why constraints improve output |
| **Context Exhaustion** | `phoenix/coding_reference/AI_BREAKTHROUGHS_CONTEXT_EXHAUSTION.md` | The pattern-matching failure mode you're in right now |

### Reference Implementations
| Directory | What to look at |
|---|---|
| `phoenix/cli/space_schema_gen/` | structures.py, pipeline.py, resolvers.py — the pattern to follow |
| `phoenix/cli/doc_schema_gen/` | builders.py, composers.py — YAML to JSON Schema with inheritance |

### Current System (what Draupnir replaces)
| File | What it tells you |
|---|---|
| `tools/agent_schema.py` | The 1700-line monolith. Read for BEHAVIOR to replicate, not code to imitate |
| `tools/inspect_schema.py` | The schema inspector. Should work unchanged with Draupnir output |

---

## What Violation Looks Like

Concrete anti-patterns. If you catch yourself doing any of these, STOP immediately:

- **Writing a function > 50 lines** — Decompose. The function is doing more than one thing.
- **Putting `Path.read_text()` in a resolver** — IO in pure code. The caller reads, you receive data.
- **Using a `name:` field value as a lookup key** — Use file path references for structural composition.
- **Globbing a directory** — Walk from root. The schema tells you what to load.
- **Adding a method to a Pydantic model** — Logic-free structures. The method belongs in `functions/pure/`.
- **Returning `dict` from a builder** — Create a typed Schema* model in structures.py. model_dump() happens ONCE at the writer boundary.
- **Using `Any` anywhere** — The data is always typed. If you think you need `Any`, you haven't understood the data at that point.
- **Creating an `unsafe/` directory** — There is no untyped data in this system. Loaders validate directly into Pydantic models.
- **Saying "I'll clean this up later"** — No. Gleipnir constraints are enforced NOW. If it's too long, split it now.
- **Skipping a phase's references** — Re-read before implementing. Post-compaction you is not pre-compaction you.

---

## Quick Orientation

**What is Draupnir?** A schema generator that replaces `tools/agent_schema.py`. It walks composition trees from schema root to sections to groups to composed to primitives, producing JSON Schema.

**Why rebuild?** The old generator forces field names to change per pipeline stage (namespace collision avoidance via renaming). This means every downstream consumer needs different field names per stage. Draupnir keeps field names stable — the filename carries the variant, not the name field.

**What pattern does it follow?** The phoenix/cli functional architecture: frozen structures, pure functions, IO at boundaries, thin pipeline composition. Type safety maintained end-to-end with Pydantic models — serialization to dict happens once at the writer boundary.

**Where is the plan?** `~/.claude/plans/warm-gliding-kitten.md`

**What phase am I in?** Check git log for what's been committed. The plan has 6 phases (0-5) plus downstream rebuild (Phase 6).
