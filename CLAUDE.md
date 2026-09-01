# Draupnir — Context Refresh Protocol

## STOP. Read this before writing any code.

You are rebuilding a schema generator. You have a design document. You probably feel like you understand the architecture well enough to start coding. **You are almost certainly wrong.**

After compaction, you have a summary — not understanding. The summary preserves conclusions but loses reasoning, constraints, and the specific shapes of things. You will produce output that looks right, compiles, and silently violates the architecture because the summary told you WHAT but not HOW or WHY NOT.

**This has happened before.** Previous LLM sessions in this project have:
- Implemented structured fields as `type: string` (silently dropping architecture)
- Flattened 8-level composition hierarchies because they "seemed redundant"
- Globbed entire directories when the design requires level-ordered loading
- Put IO in pure functions because "it's just one file read"
- Built 50+ line monolith functions while claiming to follow Gleipnir rules
- Returned `dict[str, Any]` from builders because "it's JSON Schema, dicts are natural"
- Created an `unsafe/` directory for loaders that didn't need `Any` types at all
- Created a "resolve" function when there is no resolution step — loading IS the pipeline
- Used AfterValidator on strings when the architecture requires BeforeValidator that converts strings to cached models
- Built demand-driven recursive loaders when the architecture specifies supply-driven level-ordered loading
- Written a function that returns `dict` to "pass through" YAML data, then tried to fix the type annotation instead of questioning the approach
- Called Gleipnir a "linter" while trying to make guardrail violations pass — the ultimate sign of lost architecture

None of them felt uncertain while doing it.

**The test:** Can you state three specific constraints of this project that diverge from how you'd normally write this code? Not "I should be careful" — actual constraints, with reasons. If you can't, you don't have enough context to write code. Read the CONTEXT_MAP and recovery sources below before proceeding.

---
<!-- EVERYTHING ABOVE THIS LINE IS STANDARDIZED (except the failure examples) -->
<!-- EVERYTHING BELOW THIS LINE IS PROJECT-SPECIFIC                           -->
---

## MANDATORY: Run Guardrails Frequently

```
uv run pytest tests/test_guardrails.py
```

**Run this after EVERY significant change.** Not after finishing a phase. Not at the end
of the session. After every file you write. After every function you complete. After every
edit that touches more than a few lines.

**Why frequency matters:** Architectural debt compounds silently. If you write 3 files
without running guardrails, you may have 15 violations that share a common root cause.
At 3 files, that's fixable. At 6 files, it's painful. At 10 files, you can't refactor
out of it — the architectural debt is load-bearing and the only option is fail-abort-rebuild.

**The failure mode:** "I'll run guardrails after I finish this phase." By then, the
violations are entangled with each other. Fixing one creates two more. This is the
whack-a-mole death spiral.

**The discipline:** Run early, run often. Green after every change. A violation after
one file is a 2-minute fix. A violation cluster after 6 files is a session-ending rebuild.

### Gleipnir as Diagnostic: Redirect vs Blocker

**When you are oriented**, a guardrail violation is a simple redirect. You see the
violation, understand what it means architecturally, adjust your approach, and
continue. This takes 30 seconds. Example: "bare dict in type annotation" → "oh, I
shouldn't be passing dict here — every YAML shape is a known model."

**When you have lost the architecture**, a guardrail violation becomes a blocker.
You see the violation and start trying to make it pass — changing type annotations,
trying workarounds, escalating through increasingly clever typing tricks. Each
attempt hits another guardrail. You call Gleipnir a "linter." You are now writing
code to satisfy the checker, not the architecture.

**The test:** When you hit a guardrail violation, do you immediately see the
architectural fix? If yes, you're oriented — fix and continue. If you're reaching
for workarounds, STOP. You have lost the architecture. Re-read this CLAUDE.md and
the design doc before writing another line of code.

**This has happened.** A session hit `no_bare_collections` on a function returning
`dict`. Instead of asking "why does my design have dict?", the session tried
`dict[str, object]`, then `dict[str, Any]`, then considered other typing tricks.
Each step moved further from the architecture. The user had to intervene. The
correct response was: "every YAML shape is known — the `{oneOf: [...]}` structure
is a model called `ArrayOneOf`, and Pydantic's union matching handles it without
any dict."

---

## Context Reminders for Long Sessions

This will be a long coding session with frequent compaction. After each compaction, you will lose the reasoning behind decisions. These reminders tell you WHERE YOU ARE and WHAT NOT TO DEVIATE FROM.

### After Schema Regeneration

When draupnir regenerates schemas (`uv run draupnir`), nornir must be redeployed to embed the updated schemas:

```bash
cd /Users/johnny/.ai/spaces/bragi/tools/nornir && ./deploy_gates.py
```

Do NOT use bare `cargo build` — it skips gate module deployment (maturin builds, `.so` extraction, symlink creation, verification).

### After ANY compaction, ask yourself:

1. **What phase am I in?** Check the gated plan (DRAUPNIR_REDESIGN.md §11). Find the last completed gate. That's where you are.

2. **Am I about to create a resolve function?** There is no resolution. String refs ARE graph edges. If you're writing `resolve_`, STOP.

3. **Am I hand-writing input models?** Input models are GENERATED from schemas. If you're writing `InputAtom` or adding `| str` to ref aliases, STOP.

4. **Am I using yaml.safe_load?** The Rust gate reads files. Zero yaml imports in the codebase. If you're importing yaml, STOP.

5. **Am I building recursive dispatch?** All recursive code was deleted. Flat loop over topological sort. If you're writing `build_fn: Callable`, STOP.

6. **Are my functions small and single-purpose?** Run `uv run pytest tests/test_guardrails.py` NOW.

7. **Is IO only in the gate and writer?** If `Path.read_text()`, `open()`, or `yaml` appears in Python, STOP. The gate handles reads.

8. **Have I run guardrails recently?** `uv run pytest tests/test_guardrails.py` — if you haven't run it in the last 2-3 changes, run it NOW. Architectural debt compounds faster than you think.

9. **Am I using leading underscores?** No `_private` functions. Every function is a public composable unit.

10. **Am I reaching for `dict`?** This is a CANARY. We pass typed Pydantic models everywhere. YAML validates straight into models. If you want dict, you've lost the architecture. Re-read §7 and the architecture paragraph below.

11. **Is Gleipnir a redirect or a blocker right now?** If a guardrail violation is a simple "oh, do X instead" → you're oriented. If you're trying workarounds to make it pass → STOP. You've lost the architecture. Re-read this file. Every YAML shape is known. Every known shape has a model. There are no arbitrary dicts.

### The architecture in one paragraph:

Draupnir reads Verdandi YAML files (~348 files across 15 level directories). A Rust PyO3 gate reads each file, validates against JSON Schema, and returns a JSON string. `model_validate_json` on generated input models (with `str` ref fields) produces the cache. String refs stay as strings — they are graph edges in a NetworkX DiGraph. The graph gives topological sort (build order), in-degree >= 2 ($defs detection), and adjacency (which children belong to each parent). A flat loop walks nodes in topological order, dispatches each to its type-specific builder via the `built` dict, and assembles SchemaDocuments. The writer serializes to JSON. Two impure boundaries: gate reads files, writer writes files. Everything between is pure.

---

## Functional Programming Discipline

These principles are not optional style preferences. They are the architectural
response to structural problems in LLM-generated code. Following them is how you
automatically pass Gleipnir. Fighting them is how you produce confident, plausible,
structurally wrong output.

### Hemingway Coding: Each function does ONE thing

"What is the ONE thing this function does?" If you can't answer in one sentence,
you're not ready to write it. 16 lines of functional code replaced 10+ files of
scattered datetime logic. Not through clever compression — through eliminating waste.

**The question:** What is the functional primitive here?
**The process:** SLOW DOWN → scan for patterns → identify actual needs → question
assumptions → design minimal → let composition emerge.

**Reference:** `phoenix/coding_reference/AI_BREAKTHROUGHS_HEMINGWAY_CODING.md`

### IO Externalization: The two-boundary architecture

90%+ of errors cluster at IO boundaries. Draupnir has exactly TWO impure files:
`loader.py` (reads YAML) and `writer.py` (writes JSON). Everything between is pure
computation on frozen models.

If you put `Path.read_text()` in the builder, you've punched a hole in the wall.
The builder receives a cache of frozen models. It cannot and should not access files.
The error field for draupnir is ONLY those two impure files — the rest is provably
safe given valid inputs.

**Reference:** `phoenix/coding_reference/AI_BREAKTHROUGHS_IO_EXTERNALIZATION.md`

### Safety Taxonomy: Import path IS the safety contract

```
functions/pure/builder.py   → pure computation, no side effects, assumes valid inputs
functions/impure/loader.py  → has side effects (reads files), assumes valid inputs
functions/impure/writer.py  → has side effects (writes files), assumes valid inputs
```

The directory structure encodes the safety contract. A function in `pure/` that reads
a file is in the wrong location — that's an architectural problem, not a naming problem.

**Reference:** `phoenix/coding_reference/AI_BREAKTHROUGHS_SAFETY_TAXONOMY.md`

### Errors Are Signal: Error clusters point to architectural problems

When guardrails report multiple long functions in builder.py, the problem is NOT
those functions. The problem is the builder architecture. Error clusters are a MAP:

- **Type clusters** → WHAT is wrong (scattered Any = boundary discipline broke)
- **Location clusters** → WHERE to fix (all in pipeline.py = pipeline architecture wrong)
- **Combined** → the optimization opportunity

**NEVER silence errors** (type: ignore, quarantine expansion, "various other violations").
Silencing destroys the map.

**Reference:** `phoenix/coding_reference/AI_BREAKTHROUGHS_ERRORS_ARE_SIGNAL.md`

### Context Exhaustion: The failure mode you're entering right now

As this session progresses, you will shift from thinking to pattern matching. The
warning signs are specific:

- **Dismissiveness:** "These are style rules, not broken functionality"
- **Punting:** "Want me to address any specific ones?"
- **Oscillating:** First dismissing, then frantically doing everything
- **Rationalizing:** Finding reasons why rules don't apply here

**Pattern matching feels efficient. You're completing tasks. You feel confident.
That confidence is the symptom, not the cause.** The cause is context exhaustion.

When you notice these signs: STOP. Don't overcorrect. End the session or re-read
this CLAUDE.md.

**Reference:** `phoenix/coding_reference/AI_BREAKTHROUGHS_CONTEXT_EXHAUSTION.md`

### Refactoring Discipline: STOP before fixing

When you see error lists: **DO NOT start fixing.** Read ALL errors. Find the PATTERN.
Identify the functional primitive. Secure the boundary. Errors disappear naturally.

Whack-a-mole (fix A → creates B → fix B → breaks A) means you're treating symptoms.
If the code gets worse, throw out changes and start over with architecture.

**Reference:** `phoenix/coding_reference/AI_BREAKTHROUGHS_REFACTORING_DISCIPLINE.md`

### Naming Is Instruction: Names overpower instructions 200:1

Names are encountered hundreds of times per session. Instructions are read once.
Your training data is full of `utils.py`, `helpers.py`, `misc/` — those names are
traps for the next session.

Every name you choose teaches the next LLM what this system IS. `structures/` teaches
"data containers." `functions/pure/` teaches "safe computation." `loader.py` teaches
"this reads files." Name for the naive future reader, not for your current informed self.

**Reference:** `phoenix/coding_reference/AI_BREAKTHROUGHS_NAMING_IS_INSTRUCTION.md`

### The Economic Model: Gleipnir makes bad patterns expensive

Gleipnir is NOT a quality certification system. Passing means "hasn't triggered
failure detectors yet." Failing means "violation detected — investigate."

The economics: functional patterns pass freely (cheap). OOP/monolith patterns fail
repeatedly (expensive). Over time, the only winning move is to actually write good
functional code. You can't game tight constraints with OOP — god classes, deep
inheritance, massive constructors all violate multiple constraints simultaneously.

**If you're fighting guardrails, you have an architectural problem.**

**Reference:** `phoenix/coding_reference/AI_BREAKTHROUGHS_ECONOMIC_MODEL.md`

---

## Gleipnir

**MANDATORY:** Run `uv run pytest tests/test_guardrails.py` FREQUENTLY during development.

Key constraints (enforced, not advisory):
- **Functions do one thing** — if it's getting long, decompose
- **Few parameters** — if you need more, create a structure
- **Shallow nesting** — extract inner logic into named functions
- **Quarantine budget** — IO-touching files are limited

Gleipnir enforces these structurally. If a check fails, the function does too much — extract, don't compress.

---

## Coding Discipline References

These are stable methodology references not covered by the CONTEXT_MAP. They don't change
when the project's architecture or documentation evolves.

### Functional Programming
| Document | Path | What it tells you |
|----------|------|-------------------|
| **Hemingway Coding** | `phoenix/coding_reference/AI_BREAKTHROUGHS_HEMINGWAY_CODING.md` | Each function does ONE thing — the functional primitive |
| **IO Externalization** | `phoenix/coding_reference/AI_BREAKTHROUGHS_IO_EXTERNALIZATION.md` | 90%+ of errors at IO boundaries — externalize, don't secure |
| **Safety Taxonomy** | `phoenix/coding_reference/AI_BREAKTHROUGHS_SAFETY_TAXONOMY.md` | Import path IS the safety contract — pure/impure/unsafe |
| **Context Exhaustion** | `phoenix/coding_reference/AI_BREAKTHROUGHS_CONTEXT_EXHAUSTION.md` | Overconfidence + pattern matching = catastrophic errors |
| **Errors Are Signal** | `phoenix/coding_reference/AI_BREAKTHROUGHS_ERRORS_ARE_SIGNAL.md` | Error clusters are maps — silencing destroys the map |
| **Economic Model** | `phoenix/coding_reference/AI_BREAKTHROUGHS_ECONOMIC_MODEL.md` | Gleipnir makes bad patterns expensive, good patterns free |
| **Refactoring Discipline** | `phoenix/coding_reference/AI_BREAKTHROUGHS_REFACTORING_DISCIPLINE.md` | STOP before fixing — find the pattern, secure the boundary |
| **Naming Is Instruction** | `phoenix/coding_reference/AI_BREAKTHROUGHS_NAMING_IS_INSTRUCTION.md` | Names overpower instructions 200:1 — name for naive readers |
| **Mental Map Architecture** | `phoenix/coding_reference/AI_BREAKTHROUGHS_MENTAL_MAP_ARCHITECTURE.md` | Codebase is spatial graph — FP creates simple graphs |
| **Boundary Security** | `phoenix/coding_reference/AI_BREAKTHROUGHS_BOUNDARY_SECURITY.md` | Visualize error field — can you imagine all failure modes? |
| **Sandbox Model** | `phoenix/coding_reference/AI_BREAKTHROUGHS_SANDBOX_MODEL.md` | "There is no door" — violations architecturally impossible |
| **LLM Coding Quality** | `outputs/LLM_CODING_QUALITY_v2.md` | The 6 structural problems and architectural responses |

### Behavioral Reference (read for behavior, not code to follow)
| Resource | What it tells you |
|----------|-------------------|
| `src/draupnir_old/` | Old draupnir code — read for BEHAVIOR to replicate, not code to follow |
| `tools/agent_schema.py` | The 1700-line monolith draupnir replaces |
| `tools/inspect_schema.py` | Schema inspector — should work unchanged with new output |

---

<!-- Salvaged memory residue routed into draupnir. Additive only. -->

## You Will Get These Things Wrong (salvaged)

### Generating conditional `if` blocks without a `required` guard
**Detection:** If you build a JSON Schema `if/then/else` from `only_when`/`always_when`/`not_when` and the `if` block has `properties` but no `required`...
**Why it's wrong:** When the predicate field is absent from the data, an `if` block that only constrains `properties` is vacuously true — the `then`/`else` fires (or fails to fire) incorrectly. The predicate field must be listed in the `if` block's `required` so the condition only matches when the field is actually present.
**Recovery:** Add the predicate field name to the `if` block's `required` tuple for both same-section and cross-section conditional builders.

## Recovery Sources (salvaged)

### The input gate (file-validation boundary) — Rust internals
The gate crate is `nornir/gates/gate_verdandi_input/`, built/deployed via `nornir_deploy --build gates`. Internally it does `fs::read_to_string(file_path)` → `yaml_to_json()` (from `format_core`) → validate against the JSON Schema → return the validated JSON string. Compiled schemas are held in a `Mutex<HashMap<String, Validator>>` cache. On failure it raises `ValueError` — it does NOT return a dict or an `{"ok": ...}` envelope. Python calls `Model.model_validate_json(json_string)` on the result; no `yaml.safe_load`, `json.loads`, or `file.read_text()` in Python.

## Project Notes (salvaged)

### Generated input models wrap refs in `RootModel[str]`, not bare `str`
`datamodel-code-generator` emits ref fields as `RootModel[str]` subclasses (e.g. `PatternRef(RootModel[str])`, `SimplegroupItemRef(RootModel[str])`), not plain `str` fields. Access the actual string via `.root`. Zone dicts come through as `RootModel[dict[str, RefType] | None]` — unwrap `.root` to get the dict, whose values are themselves `RootModel[str]` instances. Any code that extracts refs to build the graph (or that reads zone properties) must unwrap RootModel at each layer: if `isinstance(model, RootModel)` unwrap `.root`, then branch on dict / list / str / BaseModel.

### `export_input_schemas.py` self-reference bug
When exporting input schemas, ref fields are rewritten to `{"type": "string"}` (refs are cache-key strings in YAML) and removed model validators are re-encoded as constraints (oneOf/anyOf/const). The model currently being exported must be EXCLUDED from this string-replacement pass — otherwise the schema replaces references to its own type and is corrupted (this bug was hit and fixed).

### The builder dispatch table must live in `orchestrate`
The compile loop's dispatch table maps each of the 14 levels to its builder, importing builders from all four lower levels (primitive, simple, composed, assembled). Only the orchestrate level may legally import across all those levels, so the dispatch table must stay in `orchestrate` (the compile loop) — it cannot be extracted into a lower-level `dispatch.py` without violating the zone/level import rules.

---
<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!-- EVERYTHING ABOVE THIS LINE IS BEHAVIORAL (human-maintained, empirical) -->
<!-- EVERYTHING BELOW THIS LINE IS DYNAMIC ORIENTATION (agent-regenerated)  -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->
---

## Dynamic Orientation

@./CONTEXT_MAP.md

<!-- CONTEXT_MAP.md provides: purpose, primary references, documentation references
     with freshness flags, schema references, upstream/downstream dependencies,
     source code map, context refresh guide, known issues / active work.
     Regenerated by summarizer agents. Do not edit CONTEXT_MAP.md manually. -->
