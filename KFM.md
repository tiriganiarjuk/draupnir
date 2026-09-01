# KFM — Draupnir

Known failure modes. Each entry records something that actually went wrong here, badly
enough or often enough to be worth writing down: a mistake that kept recurring, one that
was tedious to rediscover, or one that cost hours nobody wanted to spend twice.

**This file is deliberately not linked from anything.** Not the CONTEXT_MAP, not CLAUDE.md,
not the README. It has a name that tells you nothing on purpose. That is not tidiness — it
is the point:

> A list of failure modes read *before* you have a model of the project is not a warning,
> it is a set of suggestions. Naming a mistake supplies it. And a vivid catalogue of nine
> concrete failures shadows the orientation gate it sits above — a reader absorbs the
> stories, feels informed about the project, and skips the documents that would actually
> have oriented them.
>
> Read at the right moment — when something has already gone wrong, or when you are about
> to touch a part with a known history — the same entries are worth what they cost. The
> content is not the problem. The timing is.

The mechanism for *when* a reader gets sent here is undecided. Until it is decided, nothing
points here, and that is intentional rather than an oversight.

**If you have landed here anyway:** read it as history, not as instruction. Nothing below
is a description of the tree as it stands now — check anything concrete against the code
before acting on it.

**Maintenance:** an entry retires when its vector is gone. A trap guarding code that no
longer exists is worse than no trap, because it is the rigid layer asserting something
false. This has already happened once. Nothing automatic enforces it.

---

## You Will Get These Things Wrong

### Creating a "resolve" function
**Detection:** If you find yourself writing `def resolve(`, `resolve_refs`, `resolve_walked_`, `ResolvedNode`...
**Why it's wrong:** There is no resolution step. String refs in YAML files ARE the graph edges. They stay as strings in the generated input models. The network graph uses them directly. Three attempts at resolution functions all failed.
**Recovery:** Read `src/draupnir/WHY_NETWORK_GRAPHS_ARE_THE_SOLUTION.md`

### Hand-writing input model types
**Detection:** If you find yourself writing `InputAtom`, `InputPattern`, or adding `| str` to existing ref type aliases...
**Why it's wrong:** Input models are GENERATED from input schemas using `datamodel-code-generator` (same pattern as Regin). Adding `| str` to existing ref type aliases poisons output schemas for the entire pipeline. This was tried and catastrophically failed.
**Recovery:** Read `src/draupnir/WHY_WE_KEEP_GETTING_STUCK.md` "Attempt 3". Use the schema export + generation approach.

### Putting IO outside the gate/writer boundary
**Detection:** If you find yourself writing `Path.read_text()`, `open()`, `yaml.safe_load()` in Python...
**Why it's wrong:** The Rust PyO3 gate reads files. It takes `file_path`, not `yaml_content`. No `yaml.safe_load()` in Python. The gate IS the IO boundary for reads. `writer.py` is the IO boundary for writes. Everything between is pure.
**Recovery:** Read `logic/impure/loader/ffi.py` — that's the gate FFI wrapper.

### Using BeforeValidator for ref types
**Detection:** If you find yourself writing `BeforeValidator(ref_from_cache)` on ref fields...
**Why it's wrong:** The old "models hold models" approach with BeforeValidator is gone. The new architecture uses generated input models with `str` ref fields. String refs stay as strings — they are the graph edges. No cache lookup during validation.
**Recovery:** Read `src/draupnir/WHY_NETWORK_GRAPHS_ARE_THE_SOLUTION.md` "Input Models: Generated, Not Hand-Written"

### Building recursive dispatch
**Detection:** If you find yourself writing `build_fn: Callable`, `build_or_ref`, `build_model` with recursive calls...
**Why it's wrong:** Recursive dispatch creates upward dependencies (leaf calls root). Three attempts failed. 28 Callable DI violations. The architecture correctly forbids this. All recursive dispatch code has been deleted.
**Recovery:** Read `src/draupnir/WHY_WE_KEEP_GETTING_STUCK.md`. The solution is a flat loop over topological sort order using the `built` dict.

### Reaching for `dict` (CANARY — you may need a context refresh)
**Detection:** If you find yourself writing `dict[str, ...]`, passing dicts between functions, building dicts from YAML data, or using dict as an intermediate representation...
**Why it's wrong:** This system passes TYPED PYDANTIC MODELS everywhere. YAML validates straight into models. Models hold models. The builder receives models and returns models. `model_dump()` happens ONCE, at the writer boundary. If you're reaching for dict, you've lost the architecture — you're probably thinking in generic Python instead of this system's model-holds-model design.
**Recovery:** STOP. This is a canary. Re-read DRAUPNIR_REDESIGN.md §7 and the architecture paragraph in "Context Reminders" below. The answer is almost never dict — it's a typed model or a typed model field.

### Treating YAML data as "arbitrary" or "dynamic"
**Detection:** If you find yourself writing "arbitrary YAML dict", "dynamic structure", "unknown shape", or handling YAML data as untyped...
**Why it's wrong:** Every YAML shape in Verdandi is KNOWN. There are exactly 14 level formats, each with a known structure. The `{oneOf: [...]}` dict is not "arbitrary" — it's a specific, known shape with a model (`ArrayOneOf`, `SuperarrayOneOf`). If you think a YAML value is untyped, you haven't read the YAML files for that level.
**Recovery:** Read the actual YAML files in `tools/verdandi/<level>/`. Identify the shape. Create or find the model for it. Use Pydantic's union matching if a field accepts multiple known shapes.

### Adding methods to models
**Detection:** If you find yourself adding `def`, `@property`, `@model_validator` that contains logic, classmethod factories...
**Why it's wrong:** Models in `structures/` are frozen data containers. Zero methods. Validators that enforce structural invariants (like "at least one of required/optional/conditional") are the ONE exception — and even those are simple boolean checks, not logic.
**Recovery:** Look at the models. They're `ConfigDict(frozen=True)` with typed fields. That's it.

### Writing long functions
**Detection:** If you're still writing and the function keeps growing...
**Why it's wrong:** A long function is doing more than one thing. Decompose NOW, not later. "I'll clean this up later" means it ships broken. Gleipnir will catch it — but the real problem is architectural, not numerical.
**Recovery:** Split the function. Each piece does one thing.

### Using `Any` anywhere
**Detection:** If you find yourself writing `: Any`, `dict[str, Any]`, `-> Any`...
**Why it's wrong:** Every value in this system has a known type. The YAML shapes are known. The models are typed. The output is typed. If you think you need `Any`, you haven't understood the data at that point.
**Recovery:** Trace the data. What type is it ACTUALLY? Create a model for it.

### Re-exporting from `__init__.py`
**Detection:** If you find yourself writing `from .fields import Pattern, Atom` in `__init__.py`...
**Why it's wrong:** `__init__.py` files are ALWAYS EMPTY. Direct imports only: `from draupnir.structures.fields import Pattern`.
**Recovery:** Delete the re-export. Fix the import at the call site.

### Calling the structures directory "models"
**Detection:** If you create `src/draupnir/models/`...
**Why it's wrong:** The convention is `structures/`. Models is the Pydantic term. Structures is our term. The directory has always been called structures.
**Recovery:** Rename to `structures/`.

### Using leading underscore names
**Detection:** If you find yourself writing `def _validate_ref(`, `def _build_properties(`, `_helper_function`...
**Why it's wrong:** No leading underscore names. Period. The "private" convention is an OOP pattern for hiding implementation behind interfaces. In FP, every function is a composable public unit. If a function does one thing and is pure, there's no reason to hide it.
**Recovery:** Remove the underscore. If the name collides, choose a better name.

### Using nullable wrapping in schema export
**Detection:** If you find yourself writing `SchemaNullableObject`, `SchemaNullType`, or wrapping sections in `oneOf: [schema, {type: null}]`...
**Why it's wrong:** Nullable is removed. Investigation confirmed that generated Pydantic models collapse nullable and optional into `| None = None` (row 3). TOML has no null. Pipeline processors don't distinguish. The oneOf wrapping was dead weight.
**Recovery:** Use `optional` zone instead. See `tools/verdandi/PLAN_SCHEMA_ZONE_UNIFICATION.md`.

### Detecting cross-section conditionals by internal dots
**Detection:** If you find yourself writing `"." in when.field` to detect cross-section conditionals...
**Why it's wrong:** Cross-section paths now use a leading dot: `.indirect.dispatch.dispatch_mode`. The old heuristic (`"." in field`) is ambiguous at the schema root level where siblings are sections. The new detection is `when.field.startswith(".")`.
**Recovery:** Use `startswith(".")` and strip the leading dot before splitting into path segments.

---
