# Draupnir Redesign — Verdandi Integration

Capture document for the architectural changes needed to make draupnir
consume Verdandi's composition hierarchy instead of toolcompose.

---

## 1. Major Architectural Changes

### What Changed: Toolcompose → Verdandi

**Toolcompose** had 7 structural categories:
- primitives/ (68 files) — flat type + requirement
- composed/ (57 files) — type adoption, arrays, oneOf
- groups/ (25 files) — flat objects
- arrays/ (18 files) — arrays of groups
- supergroups/ (7 files) — groups with sub_components
- superarrays/ (3 files) — arrays of supergroups
- sections/ (15 files) — top-level containers
- schema/ (11 files) — root definitions

**Verdandi** has 14 levels in 4 tiers:
- **Fields:** pattern, atom, enum, element, union
- **Simple containers:** tuple, simplearray, simplegroup
- **Complex containers:** group, array, superarray
- **Top level:** section, shallowsection, schema

### Key Structural Differences

1. **Primitives split into 5 field levels** — pattern, atom, enum, element, union
   each carry exactly one concern. No more "type + requirement + enum values"
   in a single file.

2. **composed/ eliminated entirely** — its contents distributed across element,
   union, tuple, simplearray, simplegroup based on what they actually ARE.

3. **supergroups/ merged into group/** — the distinction was artificial. Groups
   can have both fields and containers sections.

4. **New tier: simple containers** — tuple, simplearray, simplegroup explicitly
   cannot contain other containers. This is a compile-time guarantee.

5. **shallowsection/ is new** — for render schemas where fields mix with
   containers at top level. Max 2 containers per shallowsection.

6. **Reference model changed** — everything is `level/filename` paths.
   No name-based lookups. File path IS identity.

7. **Variant naming flipped** — unadorned name = final target (destination).
   `_raw` and `_resolved` are intermediate stages.

8. **Requirement placement changed** — `required`/`optional`/`conditional`
   live at the CONTAINER level, not on the field itself. Except
   `required: mandatory` on elements (compile-time lock).

9. **Conditional keywords formalized** —
   - `only_when`: if and only if (required when true, FORBIDDEN when false)
   - `always_when`: required when true (no effect when false)
   - `not_when`: forbidden when true (no effect when false)

10. **fields/containers split in groups** — two separate YAML sections
    making tier boundaries visible.

---

## 2. Impact on Draupnir Processing

### What draupnir currently does

**Location:** `tools/draupnir/` — ~2,900 lines of source, ~3,650 lines of tests.

**4-stage pipeline:**
```
YAML → [Loaders] → Raw Models → [Walkers] → Walked Models
     → [Resolvers] → Resolved Models → [Builders] → JSON Schema
```

**Architecture:**
- Frozen Pydantic models throughout (no methods, no mutation)
- Pure/impure split: loaders+writers are impure, walkers+resolvers+builders are pure
- IO via dependency injection (SchemaLoaders passed to pure code)
- Type safety end-to-end (no dict[str, Any])
- model_dump_json() only at writer boundary

**Key processing:**
- **Loaders** — read YAML, validate into Raw models (RawPrimitive, RawComposed,
  RawGroup, RawArray, RawSection, RawSchema)
- **Walkers** — follow file references, load children, classify composed fields
  (thin/structural/array/blocklist), build tree (WalkedSchema)
- **Resolvers** — type chain resolution (primitive.type → primitive → ... → JSON type),
  requirement accumulation, blocklist expansion (ResolvedSchema)
- **Builders** — convert resolved tree to JSON Schema output models, detect shared
  groups for $defs/$ref deduplication (SchemaDocument)

**Two reference models currently:**
- File-based (groups+): `security_paths: groups/security_paths.yaml`
- Name-based (primitives): `agent_name: agent_name` (pool lookup)

**$defs/$ref support (newest feature):**
- `source_ref` tracked from walker → resolver → builder
- `collect_shared_groups()` finds groups used more than once
- Shared groups go to `$defs`, subsequent references become `$ref`

### What needs to change

#### 2.1 Input Parsing

**Before:** Read toolcompose YAML, understand 7 categories by directory.
**After:** Read Verdandi YAML, understand 14 levels by directory.

The parser needs to know:
- Which directory = which level
- What fields each level expects
- How references work (`level/filename` without `.yaml`)

#### 2.2 Type Resolution

**Before:** Primitives had type+requirement inline. composed/ did `$ref`.
**After:** Types build bottom-up through the hierarchy. An atom carries
the type. An element inherits from an atom and adds format. A union
composes multiple atoms/elements via oneOf.

Draupnir needs to FOLLOW the reference chain:
```
simplegroup/parameter_item
  → required: param_name: atom/kebab_string
    → atom/kebab_string: type: string, pattern: pattern/kebab
      → pattern/kebab: regex: "^[a-z0-9]+(-[a-z0-9]+)*$"
```

#### 2.3 Schema Generation

**Before:** Flat-ish. Each schema section maps to a JSON Schema object.
**After:** Hierarchical. The 4-tier composition means draupnir walks a
deeper tree but with clearer boundaries at each level.

The `$defs/$ref` plan (from the pre-existing design) becomes MORE natural
with Verdandi — each level naturally maps to a `$def` entry.

#### 2.4 Compile-Time Enforcement (NEW)

Draupnir gains new validation responsibilities:
- **Tier boundary enforcement** — references only point downward
- **Mandatory element verification** — elements with `required: mandatory`
  must appear somewhere in the schema
- **Container limits** — max 2 containers per shallowsection
- **No-mixing rule** — schema uses all-section OR all-shallowsection
- **Conditional validity** — conditional keywords reference fields that
  exist in the same container

---

## 3. What Survives vs What Dies

### Survives (architecture)

- **4-stage pipeline pattern** — Load → Walk → Resolve → Build still works.
  The stages change contents but the flow is sound.
- **Pure/impure boundary** — loaders+writers impure, everything else pure.
  This is even cleaner with Verdandi's uniform reference model.
- **Frozen Pydantic models** — still the right choice.
- **$defs/$ref mechanism** — becomes MORE natural. Each Verdandi level
  maps cleanly to a $def category.
- **SchemaDocument output model** — JSON Schema output doesn't change.
  Only how we arrive at it changes.
- **Gleipnir constraints** — still enforced.

### Dies (toolcompose-specific)

- **RawPrimitive / RawComposed** — these two models encoded the
  primitive/composed split that no longer exists. Replaced by per-level
  Raw models (RawPattern, RawAtom, RawEnum, RawElement, RawUnion, etc.)
- **Type chain resolution** — `collect_type_chain()` followed
  `primitive.type → primitive → ... → JSON type`. Verdandi atoms carry
  the JSON type directly. Elements inherit from atoms. No chains.
- **Composed field classification** — `is_structural_composed()`,
  `is_composed_array()`, `is_blocklist_composed()` — composed/ is gone.
  Each type is self-describing by its level directory.
- **Name-based pool lookups** — `build_primitives_pool()` indexed by name.
  Verdandi uses path-based references everywhere. Pool becomes a path cache.
- **Blocklist expansion** — `build_blocklists()` expanded PATH_BLOCKLIST
  imports. Verdandi uses `excludes: [pattern/traversal, ...]` directly
  on atoms. The mechanism is simpler and explicit.
- **Requirement on primitives** — `requirement: mandatory/required/optional`
  was on each primitive. Now lives at the container level.
- **Synthetic group creation** — `walk_composed_to_group()` created groups
  from structural composed fields. simplegroups exist natively now.
- **Supergroup/group distinction** — gone. Groups have fields + containers.

### Transforms (concept survives, implementation changes)

- **Type chain** → **Inheritance chain**: element.inherits → atom → pattern.
  Shorter, more explicit, same idea.
- **Requirement inheritance** → **Container-declared requirement**:
  simplegroup/group says `required: {field: type}` vs `optional: {field: type}`.
- **Composed arrays** → **simplearray**: explicit level, clearer semantics.
- **Structural composed** → **simplegroup**: was a synthetic group, now native.
- **source_ref tracking** → **path identity**: every Verdandi file IS its
  own identity (`level/filename`). No need for separate source_ref — the
  reference path itself is the dedup key.

---

## 4. The Path-Based Tree Model

### Everything is a path relative to root

This is the single biggest processing change. Every reference in Verdandi
is `level/filename` — a relative path from the Verdandi root. This means:

1. **The entire type system is a directory tree.** Loading a schema is
   walking a filesystem tree where directory names encode the level and
   filenames encode the identity.

2. **Resolution is tree traversal.** Follow paths down, resolve leaves
   first, compose upward. No pool lookups, no name collisions, no
   classification heuristics.

3. **Deduplication is path equality.** If two containers reference
   `atom/kebab_string`, that's the same node. The path IS the dedup key.
   No `source_ref` tracking needed — the reference string itself is the
   identity.

4. **Caching is trivial.** Once `atom/kebab_string` is loaded and resolved,
   cache by path. Every subsequent reference hits the cache. The tree
   becomes a DAG with shared leaves.

### Level names as processing dispatch

The directory name isn't just organization — it's a **processing instruction**.
Each level name tells draupnir HOW to process its contents:

| Level | Processing semantics |
|-------|---------------------|
| `pattern/` | Extract regex, produce JSON Schema `pattern` or `not.pattern` |
| `atom/` | Base JSON type + pattern refs + exclusion refs → JSON Schema type node |
| `enum/` | `values` list → JSON Schema `enum` array |
| `element/` | Inherit from atom/enum, add `format` keyword, check `mandatory` |
| `union/` | Members list → JSON Schema `oneOf` (NOT a schema-native construct — Verdandi shorthand) |
| `tuple/` | Ordered items list → JSON Schema `prefixItems` + `items: false` (NOT native — shorthand) |
| `simplearray/` | Single item ref → JSON Schema `type: array, items: {...}` |
| `simplegroup/` | Fields by requirement → JSON Schema `type: object` (flat, no nesting) |
| `group/` | Fields + containers split → JSON Schema `type: object` (nesting allowed) |
| `array/` | Items ref (simplegroup) → JSON Schema array with object items |
| `superarray/` | Items ref (group) → JSON Schema array with complex object items |
| `section/` | Components only → JSON Schema object (no direct fields) |
| `shallowsection/` | Fields + containers mixed → JSON Schema object (max 2 containers) |
| `schema/` | Root → JSON Schema document with $defs |

**Key insight: `union/` and `tuple/` are NOT JSON Schema constructs.**
They are Verdandi composition shorthands that draupnir transparently
converts to JSON Schema:
- `union/path_any` with members `[atom/path_relative, atom/path_absolute]`
  → `oneOf: [{type: string, pattern: ...}, {type: string, pattern: ...}]`
- `tuple/dispatch_batch_size` with items `[atom/integer, atom/integer]`
  → `type: array, prefixItems: [{type: integer}, {type: integer}], items: false`

### Potential additional shorthands

#### `limits/` level — numeric constraint definitions

Parallel to how `pattern/` works for strings. Patterns define reusable
regex constraints that atoms reference. Limits would define reusable
numeric constraints that atoms reference.

**The problem:** batch_size needs `min: 1, max: 1000` (or similar).
Currently this lives as a bare `atom/integer` with no constraint, or
requires ad-hoc `minimum:` fields on atoms. No reuse, no composition.

**Design exploration — limits as reusable constraint definitions:**

```yaml
# limits/positive.yaml
minimum: 1
description: Must be at least 1 (zero excluded)

# limits/non_zero.yaml
exclusive_minimum: 0
description: Must not be zero (negative allowed)

# limits/range_inclusive.yaml  ← generic? or specific instances?
minimum: 1
maximum: 1000
description: Bounded range, both ends included

# limits/ceiling_inclusive.yaml
maximum: 100
description: Upper bound, inclusive

# limits/floor_exclusive.yaml
exclusive_minimum: 0
description: Lower bound, exclusive (strictly greater than)
```

**Open question: generic constraints vs specific instances?**

Option A — Generic constraints, atoms parameterize:
```yaml
# limits/positive.yaml → reusable "≥1" constraint
# atom/batch_count.yaml
type: integer
limits: limits/positive
```
But this doesn't carry the max. We'd need to stack limits or
add parameters.

Option B — Specific named instances:
```yaml
# limits/batch_count_range.yaml
minimum: 1
maximum: 1000
description: Batch count between 1 and 1000

# atom/batch_count.yaml
type: integer
limits: limits/batch_count_range
```
More files but each is self-contained. Follows the pattern/ model
where each file is one specific constraint.

Option C — Composable limits (atom references multiple):
```yaml
# atom/batch_count.yaml
type: integer
limits: [limits/positive, limits/ceiling_1000]
```
Like `excludes:` on atoms — list of constraint refs that combine.

**How atoms would reference limits (parallel to pattern):**
```yaml
# atom/string_plain.yaml  (existing — pattern-based)
type: string
excludes: [pattern/relative, pattern/absolute]

# atom/batch_count.yaml  (proposed — limits-based)
type: integer
limits: limits/positive          # or limits: [limits/positive]
```

**What limits maps to in JSON Schema:**
- `minimum` → `minimum` (inclusive)
- `maximum` → `maximum` (inclusive)
- `exclusive_minimum` → `exclusiveMinimum`
- `exclusive_maximum` → `exclusiveMaximum`
- `multiple_of` → `multipleOf` (if ever needed)

**Batch definition use case:**

Current: `tuple/dispatch_batch_size` with `[atom/integer, atom/integer]`
and `constraint: ascending_strict`.

With limits: `tuple/dispatch_batch_size` with
`[atom/batch_min, atom/batch_max]` where each atom carries its own
limits. The tuple constraint `ascending_strict` still validates
min < max at the tuple level. But each individual value also has
bounds.

**UNRESOLVED:** Whether limits is a new level (between pattern and atom)
or a peer of pattern. Patterns constrain strings via regex. Limits
constrain numbers via bounds. Both are referenced by atoms. Both sit
below atoms in the hierarchy. Both are leaf-level, no references to
other levels.

```
pattern/  ← string constraints (regex)
limits/   ← numeric constraints (bounds)
atom/     ← references pattern/ and/or limits/
```

### Hierarchy enforcement at build time

Because paths encode levels and levels have strict containment rules,
draupnir can enforce the entire tier system at load time:

```
When loading group/metadata.yaml:
  fields section references:
    agent_name → split on "/" → level = "element" → ✓ (field tier)
    semantic_version → split on "/" → level = "atom" → ✓ (field tier)
  containers section references:
    role_expertise → split on "/" → level = "simplearray" → ✓ (simple container tier)

  If containers section referenced:
    context_required → split on "/" → level = "array" → ✗ COMPILE ERROR
    (array is complex container, group only accepts simple containers)
```

**Enforcement table:**

| Container level | Accepts in fields | Accepts in containers |
|----------------|-------------------|----------------------|
| tuple | pattern, atom, enum, element, union | — (no containers) |
| simplearray | pattern, atom, enum, element, union | — (no containers) |
| simplegroup | pattern, atom, enum, element, union, tuple, simplearray | — (no containers section) |
| array | — | simplegroup (as items) |
| group | pattern, atom, enum, element, union (+ tuple in conditionals) | tuple, simplearray, simplegroup, array |
| superarray | — | group, simplegroup (as items, including oneOf) |
| section | — | group, array, superarray |
| shallowsection | pattern→union (as fields) | simplearray, array, group (max 2) |
| schema | — | section, shallowsection |

Every reference violation is caught at load time before any resolution
begins. This is a HARD GATE — invalid references never enter the pipeline.

---

## 5. $defs as Central Architecture

### From tacked-on to foundational

In toolcompose draupnir, $defs/$ref was added late to deduplicate groups
that appeared multiple times. It used `source_ref` tracking through three
pipeline stages and a post-hoc `collect_shared_groups()` scan.

In Verdandi draupnir, $defs is the PRIMARY output strategy:

### Resolution strategy: leaves first, compose upward

```
1. Schema references sections/shallowsections
2. Sections reference groups/arrays/superarrays
3. Groups reference simple containers + arrays + fields
4. Arrays reference simplegroups
5. Simple containers reference fields (atoms/enums/elements/unions)
6. Fields reference patterns

Resolution order: patterns → enums → atoms → elements → unions
                → tuples → simplearrays → simplegroups
                → arrays → groups → superarrays
                → sections → shallowsections → schema
```

Each resolved node becomes a potential `$defs` entry. The question is
granularity — what's worth a `$def` vs inline?

### $defs granularity proposal

**Always $def (referenced by multiple consumers):**
- simplegroup/ — these are the "record types" (parameter_item, context_item, etc.)
  that appear as array items in multiple places
- group/ — complex objects referenced by sections

**$def when shared (same path appears 2+ times in tree):**
- Any node at any level that's referenced more than once

**Always inline (too small for $ref overhead):**
- pattern/ — single regex, inline is clearer
- atom/ — single type + pattern, inline is clearer
- enum/ — single values list, inline is clearer

**Judgment call:**
- element/ — atom + format. Small but carries semantic meaning.
  Could go either way.
- union/ — oneOf composition. Inlining is fine when small (2 members).
  $def when union has 3+ members or is referenced multiple times.

### Tree resolution → $defs extraction

The process:

1. **Load tree** — read schema YAML, follow all paths, build complete
   reference graph (DAG, not tree — shared nodes).

2. **Identify $def candidates** — scan DAG for nodes with in-degree > 1
   (referenced by multiple parents). These become $defs entries.

3. **Resolve leaves first** — patterns, atoms, enums resolved to JSON
   Schema fragments. Cached by path.

4. **Compose upward** — elements inherit resolved atoms. Unions compose
   resolved members. Simplegroups assemble resolved fields.

5. **Emit $defs** — shared nodes written to `$defs` section. First
   resolution builds the full JSON Schema fragment. Subsequent references
   emit `$ref: "#/$defs/level_filename"`.

6. **Build document** — schema root references sections, sections reference
   $defs or inline objects, $defs reference other $defs or inline.

### $defs naming

Path-based naming is natural:
- `atom/kebab_string` → `$defs/atom__kebab_string`
- `simplegroup/parameter_item` → `$defs/simplegroup__parameter_item`
- `group/metadata` → `$defs/group__metadata`

The level prefix prevents name collisions and makes the JSON Schema
self-documenting about where each definition originated.

---

## 6. Rebuild Approach

### Decision: Full rewrite — shell included

The old shell (cli.py, commands.py, pipeline.py, writers.py) is deeply
coupled to toolcompose. `pipeline.py` calls `load_all_primitives()`,
`build_primitives_pool()`, `build_blocklists()` — none of which exist
in Verdandi. `generate_schema()` is per-schema, wastefully reloading
everything each invocation. `resolve_paths()` points at `standards/toolcompose/`.

**The shell is rewritten, not repurposed.**

Schemas must be in sync. The transforms generate branches that match
schema diffs — if schemas are individually generated, they can drift.
The primary mode is `draupnir --all`: load everything once, export all
schemas, write all files. Single-schema mode exists only for debugging.

### Build location

**DECIDED:** Rename `src/draupnir/` → `src/draupnir_old/`, build fresh
`src/draupnir/`. Clean break — no temptation to import from old code
or preserve bad decisions because they're convenient. `draupnir_old/`
is reference-only, never imported. Delete when new code is proven.

### Pipeline: before and after

**Before (4 stages, old draupnir):**
```
YAML → Loaders → Raw → Walkers → Walked → Resolvers → Resolved → Builders → Schema
```

**After (2 phases, new draupnir):**
```
Phase A: LOAD (impure) — glob levels in order, validate YAML → Pydantic, fill cache
Phase B: EXPORT (pure) — walk model tree, identify $defs, build JSON Schema
Phase C: WRITE (impure) — serialize SchemaDocuments, write JSON files
```

There is no "resolution step." Loading IS the pipeline. Models hold
models, not strings. By the time `model_validate()` returns, every
reference field contains the actual child model from the cache.

---

## 7. Architecture: Models Hold Models

### There is no resolution. There is only loading.

A Pattern is a Pattern. An Atom is an Atom that HOLDS a Pattern (not a
string reference to one). A Union HOLDS Atoms. A Simplegroup HOLDS field
models. Every Pydantic model is in FINAL FORM from the moment it's
validated. Nothing is "resolved later."

The mechanism: YAML contains string references like `"atom/kebab_string"`.
Pydantic `BeforeValidator` converts these to actual cached model instances
during validation. By the time `model_validate()` returns, the model holds
real objects, not strings.

### The ref converter

```python
def ref_from_cache(v: Any, info: ValidationInfo) -> BaseModel:
    """BeforeValidator that replaces string refs with cached models."""
    if isinstance(v, str):
        cache = info.context["cache"]
        if v not in cache:
            raise ValueError(f"ref not in cache: {v!r}")
        return cache[v]
    return v  # already a model
```

### Typed ref annotations — hierarchy + conversion combined

```python
PatternRef = Annotated[Pattern, BeforeValidator(ref_from_cache)]
FieldRef = Annotated[
    Pattern | Atom | Enum | Element | Union,
    BeforeValidator(ref_from_cache),
]
SimpleContainerRef = Annotated[
    Tuple_ | Simplearray | Simplegroup,
    BeforeValidator(ref_from_cache),
]
ComplexContainerRef = Annotated[
    Group | Array | Superarray,
    BeforeValidator(ref_from_cache),
]
SectionRef = Annotated[
    Section | Shallowsection,
    BeforeValidator(ref_from_cache),
]
```

The `BeforeValidator` fires first (converts string → model from cache).
Then the union type check fires (rejects if wrong tier). A simplegroup
field value of `"group/metadata"` would retrieve the Group model from
cache, then fail the `Pattern | Atom | Enum | Element | Union` union
check. Hierarchy enforcement is AUTOMATIC — wrong-tier references are
type errors.

### Model definitions

**Models hold MODELS, not strings:**

```python
class Pattern(BaseModel):
    model_config = ConfigDict(frozen=True)
    regex: str
    description: str

class Atom(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["string", "integer", "boolean"]
    pattern: PatternRef | None = None      # ← holds Pattern, not "pattern/kebab"
    excludes: tuple[PatternRef, ...] = ()  # ← holds Patterns, not strings
    description: str

class Enum(BaseModel):
    model_config = ConfigDict(frozen=True)
    values: tuple[str, ...]
    description: str

class Element(BaseModel):
    model_config = ConfigDict(frozen=True)
    inherits: Annotated[Atom | Enum, BeforeValidator(ref_from_cache)]
    format: str
    required: Literal["mandatory"] | None = None
    description: str

class Union(BaseModel):
    model_config = ConfigDict(frozen=True)
    union: tuple[FieldRef, ...]   # ← holds Atom|Enum|Element models
    description: str

class Tuple_(BaseModel):
    model_config = ConfigDict(frozen=True)
    items: tuple[FieldRef, ...]
    constraint: str | None = None  # e.g. "ascending_strict"
    description: str

class Simplearray(BaseModel):
    model_config = ConfigDict(frozen=True)
    items: FieldRef               # single field ref
    description: str

class Simplegroup(BaseModel):
    model_config = ConfigDict(frozen=True)
    description: str
    required: dict[str, FieldRef] | None = None
    optional: dict[str, FieldRef] | None = None
    conditional: dict[str, ConditionalField] | None = None

class Group(BaseModel):
    model_config = ConfigDict(frozen=True)
    description: str
    fields: GroupFields | None = None
    containers: GroupContainers | None = None

class Array(BaseModel):
    model_config = ConfigDict(frozen=True)
    items: SimplegroupRef | ArrayOneOf   # union matching handles string vs {oneOf: [...]}
    description: str

class Superarray(BaseModel):
    model_config = ConfigDict(frozen=True)
    items: GroupOrSimplegroupRef | SuperarrayOneOf  # same pattern
    description: str

class Section(BaseModel):
    model_config = ConfigDict(frozen=True)
    description: str
    components: dict[str, ComplexContainerRef]

class Shallowsection(BaseModel):
    model_config = ConfigDict(frozen=True)
    description: str
    fields: dict[str, FieldRef] | None = None
    containers: dict[str, ComplexContainerRef] | None = None

class Schema(BaseModel):
    model_config = ConfigDict(frozen=True)
    version: int
    description: str
    required: tuple[str, ...]
    sections: dict[str, SectionRef]
```

**Supporting models:**

```python
class ConditionalField(BaseModel):
    model_config = ConfigDict(frozen=True)
    ref: FieldRef
    only_when: str | None = None
    always_when: str | None = None
    not_when: str | None = None

class GroupFields(BaseModel):
    model_config = ConfigDict(frozen=True)
    required: dict[str, FieldRef] | None = None
    optional: dict[str, FieldRef] | None = None
    conditional: dict[str, ConditionalField] | None = None

class GroupContainers(BaseModel):
    model_config = ConfigDict(frozen=True)
    required: dict[str, SimpleContainerRef] | None = None
    optional: dict[str, SimpleContainerRef] | None = None
    conditional: dict[str, ConditionalField] | None = None
```

### The load function

```python
LEVEL_ORDER = (
    "pattern", "enum", "atom", "element", "union",
    "tuple", "simplearray", "simplegroup",
    "array", "group", "superarray",
    "section", "shallowsection", "schema",
)

LEVEL_MODELS: dict[str, type[BaseModel]] = {
    "pattern": Pattern, "atom": Atom, "enum": Enum,
    "element": Element, "union": Union, "tuple": Tuple_,
    "simplearray": Simplearray, "simplegroup": Simplegroup,
    "group": Group, "array": Array, "superarray": Superarray,
    "section": Section, "shallowsection": Shallowsection,
    "schema": Schema,
}

def load(path: str, root: Path, cache: dict[str, BaseModel]) -> BaseModel:
    if path in cache:
        return cache[path]

    level, name = path.split("/", 1)
    data = yaml.safe_load((root / level / f"{name}.yaml").read_text())

    model = LEVEL_MODELS[level].model_validate(
        data,
        context={"cache": cache},
    )

    cache[path] = model
    return model
```

### What "valid" means at each level

| Level | Valid means |
|-------|-----------|
| pattern | regex parses, description present |
| atom | type is string/integer/boolean, pattern ref is a Pattern, excludes are Patterns |
| enum | values is non-empty list, description present |
| element | inherits is an Atom or Enum, format present |
| union | members are field-level models (2+ items) |
| tuple | items are field-level models, constraint is known keyword or absent |
| simplearray | items is a single field-level model |
| simplegroup | at least one of required/optional/conditional, values are field-level or simple-container-level (atom/enum/element/union/tuple/simplearray) |
| array | items is a Simplegroup (or oneOf of Simplegroups) |
| group | at least one of fields/containers, field values are field-level (+ tuple in conditionals), container values are simple-container or array level |
| superarray | items is a Group or Simplegroup (or oneOf mixing both) |
| section | components are complex-container-level models (group/array/superarray) |
| shallowsection | fields are field-level, containers are any container level (simplearray/array/group), max 2 containers |
| schema | sections are section/shallowsection level, required list valid |

Invalid = Pydantic ValidationError. No fuzzy states. No "partially resolved."
It loaded or it didn't.

### Load strategy: supply-driven, full tree

**Primary mode: `draupnir --all`** — guarantees fully propagated state.

The demand-driven recursive approach (load from schema root, pull in
what's needed) is elegant but the primary use case is generating ALL
schemas. This means we want every node loaded anyway.

**Supply-driven loading from the filesystem:**

The filesystem IS the dependency tree. The directory names ARE the levels.
The levels have a known ordering. Load them in order:

```
Phase 1 — LEAVES (no refs to other levels):
  load all pattern/*.yaml   → cache full of Pattern
  load all enum/*.yaml      → cache full of Enum

Phase 2 — FIELD COMPOSITION (refs to leaves only):
  load all atom/*.yaml      → cache full of Atom (holding Patterns)
  load all element/*.yaml   → cache full of Element (holding Atoms/Enums)
  load all union/*.yaml     → cache full of Union (holding fields)

Phase 3 — SIMPLE CONTAINERS (refs to fields only):
  load all tuple/*.yaml     → cache full of Tuple_
  load all simplearray/*.yaml → cache full of Simplearray
  load all simplegroup/*.yaml → cache full of Simplegroup (refs fields + tuple/simplearray)

Phase 4 — ARRAYS (refs to simplegroups only):
  load all array/*.yaml     → cache full of Array

Phase 5 — GROUPS + SUPERARRAYS (refs to fields + all containers):
  load all group/*.yaml     → cache full of Group (refs fields + simple containers + arrays)
  load all superarray/*.yaml → cache full of Superarray (refs groups + simplegroups)

Phase 6 — TOP LEVEL (refs to complex containers):
  load all section/*.yaml       → cache full of Section
  load all shallowsection/*.yaml → cache full of Shallowsection

Phase 7 — SCHEMAS (refs to sections):
  load all schema/*.yaml    → cache full of Schema
```

Each phase: glob the directory, load each YAML, validate through the
level's Pydantic model. All refs resolve from cache (guaranteed present
because lower levels loaded first). If a ref is NOT in cache → hard
error (missing file or bad reference).

**Benefits over demand-driven:**
- Filesystem glob IS the discovery mechanism — no need to chase refs
- Loading order is explicit and visible (good for progress, debugging)
- Detects orphan files (loaded but never referenced)
- Detects missing files (referenced but not loaded) — hard error
- Guarantees complete cache — every schema can export without further IO
- Simple implementation: `for level in LEVEL_ORDER: load_all(level)`

**After loading:** the cache holds every Verdandi file as a frozen
Pydantic model. Every model holds its children as actual models.
The entire composition tree is in memory. No further file reads needed.

### Export: mechanical assembly

Once the cache is populated, schema export is purely mechanical.
A Schema model is nothing but a list of Section or Shallowsection
references. Each section holds Groups, Arrays, Superarrays. Each of
those holds Simplegroups, Simplearrays, Tuples. Each of those holds
field models. Everything is already validated, already composed.

**Export per schema:**

```
for each schema in cache where level == "schema":
    1. Walk the Schema model's sections (already loaded, already valid)
    2. Collect all unique models seen (path → model) for $defs candidates
    3. Build JSON Schema properties from sections
    4. Emit $defs for shared models (same model instance from cache)
    5. Wire $refs to $defs entries
    6. Assemble SchemaDocument
    7. Write JSON
```

The builder receives a fully composed tree of frozen models. It doesn't
load anything, validate anything, or resolve anything. It just converts
Pydantic models → JSON Schema output models → JSON.

**$defs identification is trivial:** during the walk, track which cache
paths have been seen. If a path appears in two different branches of
the schema tree → $defs entry. The cache key (the path string) is the
dedup identity. Since all references to `atom/string_plain` return the
same frozen model instance from the cache, `is` comparison works.

### Two-phase pipeline

```
Phase A: LOAD (impure — file IO)
  glob each level directory in order
  load + validate each YAML into Pydantic model
  populate cache: dict[str, BaseModel]
  → result: fully populated cache, every model in final form

Phase B: EXPORT (pure — no IO, deterministic)
  for each Schema in cache:
    walk model tree
    identify shared nodes ($defs candidates)
    build JSON Schema output
    → result: SchemaDocument per schema

Phase C: WRITE (impure — file IO)
  serialize each SchemaDocument to JSON
  write files
```

Phase A is the only place that reads files. Phase B is pure computation.
Phase C is the only place that writes files. Clean boundaries.

### What this eliminates

- **No "resolution" concept** — loading IS the whole process
- **No walker stage** — the model tree IS the walked tree
- **No resolver stage** — there's nothing to resolve, models are final
- **No type chain resolution** — atoms hold Patterns directly
- **No pool construction** — level-ordered loading fills the cache
- **No composed field classification** — level directory IS the type
- **No synthetic group creation** — simplegroups are native
- **No requirement accumulation** — containers hold requirement zones
- **No intermediate models** — one model per level, always in final form
- **No "Raw" vs "Walked" vs "Resolved"** — just the model
- **No demand-driven recursion** — filesystem glob + level ordering

---

## 8. Resolved Design Questions

All questions resolved. No open items.

1. **One model per level, no "Raw" prefix.** 14 separate Pydantic models
   named after their level: Pattern, Atom, Enum, Element, Union, Tuple_,
   Simplearray, Simplegroup, Group, Array, Superarray, Section,
   Shallowsection, Schema. No generic model with discriminator — every
   level has distinct fields. No "Raw" prefix because there is no
   unresolved state. Models are in final form from validation.

2. **No walk+resolve stages. Loading IS the pipeline.** BeforeValidators
   on ref fields convert string references to cached models during
   validation. By the time model_validate() returns, the model holds
   actual child models. No intermediate stages.

3. **`limits/` level — DEFERRED.** Not needed for initial build. Batch
   sizing works fine with atom/integer + tuple constraint. Can be added
   later as peer to pattern/ without disrupting existing hierarchy.

4. **Variant chain — each schema YAML selects its own variants.** The
   schema YAML references e.g. `section/execution_resolved` vs
   `section/execution_reduced`. Draupnir doesn't know or care about
   variant relationships — it just loads whatever each schema references.

5. **No backward compatibility period. Hard cutover.** Old code renamed
   to `src/draupnir_old/` for reference. New code builds from scratch
   against Verdandi. Old tests kept as behavioral reference but not
   maintained.

6. **Fresh test suite.** Tests built alongside each implementation phase.
   Old tests in `draupnir_old/` serve as behavioral specification —
   what output shapes should look like, what edge cases exist — but
   are not adapted or maintained.

7. **Shell is fully rewritten, not repurposed.** Old shell (cli.py,
   commands.py, pipeline.py, writers.py) is tightly coupled to
   toolcompose concepts. New shell is minimal: load all → export all →
   write all. Single-schema mode for debugging only.

---

## 9. Shell & CLI Design

### Why rewrite, not repurpose

The old shell is coupled to toolcompose at every level:
- `pipeline.py` calls `load_all_primitives()`, `build_primitives_pool()`,
  `build_blocklists()` — none exist in Verdandi
- `generate_schema()` is per-schema, reloading everything each time
- `resolve_paths()` points to `standards/toolcompose/`
- `bridge_schema_sections()` is a toolcompose compatibility shim

The new architecture (supply-driven loading) loads everything once.
There is no per-schema pipeline. Repurposing the shell would mean
gutting every function while keeping the signatures — worse than
starting fresh.

### CLI interface

```
draupnir                    # default: --all (generate everything)
draupnir --all              # explicit: generate all schemas
draupnir --check            # check for drift without writing
draupnir --list             # list available schemas
draupnir <name>             # single schema (debug mode)
draupnir --verdandi-dir P   # override Verdandi root
draupnir --output-dir P     # override output directory
```

**Key change: `--all` is the default.** The old CLI required either a
schema name or `--all`. The new CLI defaults to `--all` because:
- Schemas must be in sync (transforms match schema diffs)
- Nornir gates must be regenerated together
- Loading is cheap (supply-driven populates cache once)
- Single-schema generation is only useful for debugging

### Path resolution

```python
def resolve_paths(
    verdandi_dir: Path | None,
    output_dir: Path | None,
    workspace_root: Path,
) -> tuple[Path, Path]:
    verdandi = verdandi_dir or workspace_root / "tools" / "verdandi"
    output = output_dir or workspace_root / "schemas"
    return verdandi, output
```

Verdandi root is `tools/verdandi/` (not `standards/toolcompose/`).
Output directory stays `schemas/` — the output format is the same,
only how we arrive at it changes.

### Pipeline orchestration

```python
def run_all(verdandi_root: Path, output_dir: Path, workspace: Path) -> int:
    """Load everything, export all schemas, write all files."""
    cache: dict[str, BaseModel] = {}

    # Phase A: LOAD (impure)
    load_all_levels(verdandi_root, cache)

    # Phase B: EXPORT (pure)
    schemas = export_all_schemas(cache)

    # Phase C: WRITE (impure)
    for name, doc in schemas.items():
        out = output_dir / f"{name}.schema.json"
        write_schema(doc, out)
        write_sidecar(out, workspace)
        sys.stdout.write(f"wrote {name}.schema.json\n")

    return 0
```

`load_all_levels()` is the only function that reads files.
`export_all_schemas()` is pure computation — no IO.
`write_schema()` + `write_sidecar()` write files.

### Check mode (drift detection)

Same concept as old draupnir: generate in memory, compare to on-disk.
Exit 1 if any schema has drifted.

```python
def run_check(verdandi_root: Path, output_dir: Path) -> int:
    cache: dict[str, BaseModel] = {}
    load_all_levels(verdandi_root, cache)
    schemas = export_all_schemas(cache)
    drift = False
    for name, doc in schemas.items():
        out = output_dir / f"{name}.schema.json"
        generated = serialize_schema(doc)
        if not out.exists() or out.read_text() != generated:
            sys.stderr.write(f"DRIFT   {out}\n")
            drift = True
        else:
            sys.stdout.write(f"OK      {out}\n")
    return 1 if drift else 0
```

### Writers

`serialize_schema()` and `write_schema()` carry over from old draupnir.
Same output format (JSON Schema). Same model_dump_json() boundary.
`write_sidecar()` carries over — calls `inspect_schema.py` for HTML.

### Schema output models

These carry over from old draupnir with one addition — `SchemaRef` for
`$ref` pointers. The JSON Schema output format doesn't change:

- `SchemaField` — `{type, pattern, enum, format, ...}`
- `SchemaObject` — `{type: object, properties, required, ...}`
- `SchemaArray` — `{type: array, items, ...}`
- `SchemaRef` — `{$ref: "#/$defs/..."}`
- `SchemaConditional` — `{if, then, else}`
- `SchemaDocument` — `{$schema, $id, title, properties, $defs, ...}`

---

## 10. File Structure

### Complete src/draupnir/ tree

```
src/draupnir/
  __init__.py
  cli.py                      # ~60 lines — argparse, dispatch

  structures/
    __init__.py               # empty — direct imports only
    fields.py                 # ~90 lines — Pattern, Atom, Enum, Element, Union + ref type aliases
    conditionals.py           # ~30 lines — ConditionalWhen
    simple_containers.py      # ~90 lines — Tuple_, Simplearray, Simplegroup + SimplegroupItemRef
    complex_containers.py     # ~120 lines — Array, Group, Superarray + GroupFields, GroupContainers
    top_level.py              # ~90 lines — Section, Shallowsection, Schema
    schema_output.py          # ~120 lines — SchemaField, SchemaObject, SchemaDocument, SchemaRef

  functions/
    __init__.py
    impure/
      __init__.py
      loader.py               # ~80 lines — load(), load_all_levels(), YAML IO
      writer.py                # ~60 lines — serialize_schema(), write_schema(), write_sidecar()
      pipeline.py              # ~50 lines — run_all(), run_check(), run_list()
    pure/
      __init__.py
      pydantic_validators.py  # ~45 lines — ref_from_cache BeforeValidator
      builder.py               # ~150 lines — export_schema(), collect_shared_nodes(), build_*()
```

### File size discipline

No file exceeds 150 lines. If approaching that limit, decompose.
Total source: ~1,000 lines (down from ~2,900 in old draupnir).

### What's NOT here

- No `walkers.py` — loading IS the walk
- No `resolvers.py` — there is no resolution step
- No `stabilizers.py` — no name normalization needed
- No `structures.py` monolith — split into `structures/` submodules
- No `unsafe/` directory — all data is typed
- No `commands.py` — folded into `pipeline.py` (commands were thin wrappers)

---

## 11. Gated Execution Plan

### Purpose of gates

After context compaction, you will have a summary of this design — not
the design itself. Gates force you to re-read specific sections and
validate your implementation against the ACTUAL architecture before
proceeding.

**The pattern:** implement → gate check → proceed only if aligned.

If a gate check reveals deviation from the architecture, STOP. Re-read
the relevant section. Fix the deviation. Do not rationalize it.

**MANDATORY: Run `uv run pytest tests/test_guardrails.py` after EVERY
file you write or edit.** Not just at gates. After every file. Gates
are architecture checkpoints. Guardrails are continuous structural
enforcement. If you write 3 files without running guardrails, you may
accumulate entangled violations that can't be untangled without
starting over.

---

### Phase 0: Clean Break

**Action:**
1. `mv src/draupnir src/draupnir_old`
2. Create fresh `src/draupnir/` with `__init__.py`
3. Create `structures/` and `functions/impure/` and `functions/pure/` dirs
4. Update `pyproject.toml` if needed (package location unchanged)

**Gate 0 — Isolation check:**
- [ ] `src/draupnir_old/` exists with all old code
- [ ] `src/draupnir/` exists as empty package structure
- [ ] No imports from `draupnir_old` anywhere in new code
- [ ] Old tests still importable from `draupnir_old` for reference
- [ ] `uv run pytest tests/test_guardrails.py` passes (baseline)

---

### Phase 1: Models — pydantic_validators.py + fields.py

**Build:** `functions/pure/pydantic_validators.py` (ref_from_cache) and
`structures/fields.py` (Pattern, Atom, Enum, Element, Union + ref type
aliases: PatternRef, AtomOrEnumRef, UnionMemberRef, FieldRef).

Ref type aliases live in each consumer module (not centralized) because
each module knows which model types are available at its import level.
No functions in `structures/` — `ref_from_cache` goes in `functions/pure/`.

**References to re-read BEFORE starting:**
- §7 "The ref converter" — exact ref_from_cache implementation
- §7 "Typed ref annotations" — hierarchy + conversion combined
- §7 "Model definitions" — Pattern through Union

**Tests:**
- Pattern validates from dict, rejects missing regex
- Atom with pattern ref resolves from cache
- Atom with wrong-tier ref (e.g. "group/foo") fails validation
- Element inherits from cached Atom
- Union holds cached field models
- FieldRef rejects "simplearray/foo" (wrong tier)

**Gate 1 — Model fidelity check:**
- [ ] Models are frozen (`ConfigDict(frozen=True)`)
- [ ] Models have ZERO methods (no `def`, no `@property`)
- [ ] Ref fields use `BeforeValidator(ref_from_cache)` not `AfterValidator`
- [ ] Ref fields resolve to MODELS, not strings
- [ ] No `dict[str, Any]` anywhere
- [ ] No file reads in structures/
- [ ] Each file < 150 lines
- [ ] `uv run pytest tests/test_guardrails.py` passes (run after EACH file, not just here)

---

### Phase 2: Models — containers + top level

**Build:** `conditionals.py` (ConditionalWhen), `simple_containers.py`
(Tuple_, Simplearray, Simplegroup + SimplegroupItemRef),
`complex_containers.py` (Array, Group, Superarray + GroupFields,
GroupContainers, ArrayOneOf, SuperarrayOneOf), `top_level.py`
(Section, Shallowsection, Schema + ShallowContainers).

GroupFields and GroupContainers live in `complex_containers.py` (not
`conditionals.py`) because GroupContainers needs the Array type which
is defined in the same file. Per-context conditional entry models are
defined in each container module using the appropriate ref type.

**Array/Superarray items: union matching, not dict passthrough.**
YAML items can be a string ref OR `{oneOf: [...]}`. The field type is
`SimplegroupRef | ArrayOneOf`. Pydantic's union matching handles both:
string → SimplegroupRef's BeforeValidator → cache lookup → model;
dict → SimplegroupRef fails → ArrayOneOf validates naturally as a model.
NO new validator functions needed. NO dict passthrough. If you find
yourself writing a function that handles dicts, STOP — you've lost the
architecture.

**References to re-read BEFORE starting:**
- §7 "Model definitions" — Simplegroup through Schema
- §4 "Hierarchy enforcement at build time" — enforcement table
- §1 "Conditional keywords formalized" — only_when/always_when/not_when
- Actual YAML files in `tools/verdandi/` — ground truth for field shapes

**Tests:**
- Simplegroup requires at least one of required/optional/conditional
- Group requires at least one of fields/containers
- Group fields dict accepts FieldRef, rejects SimpleContainerRef
- Group containers dict accepts GroupContainerRef (tuple/simplearray/simplegroup/array)
- Array items: string ref resolves to Simplegroup, {oneOf: [...]} resolves to ArrayOneOf
- Section components accept ComplexContainerRef only
- Schema requires exactly one of sections/shallowsections
- Shallowsection max 2 containers enforced

**Gate 2 — Hierarchy enforcement check:**
- [ ] FieldRef union type is `Pattern | Atom | Enum | Element | Union`
- [ ] SimplegroupItemRef includes field-level + Tuple_ + Simplearray
- [ ] GroupContainerRef is `Tuple_ | Simplearray | Simplegroup | Array`
- [ ] ComplexContainerRef union type is `Group | Array | Superarray`
- [ ] Array items uses union matching (SimplegroupRef | ArrayOneOf), NOT dict passthrough
- [ ] Wrong-tier refs produce ValidationError (test passes)
- [ ] All models frozen, zero methods (except structural invariant validators)
- [ ] Conditional entries enforce exactly one of only_when/always_when/not_when
- [ ] `uv run pytest tests/test_guardrails.py` passes

---

### Phase 3: Schema output models

**Build:** `schema_output.py` — carry from old draupnir. SchemaField,
SchemaObject, SchemaArray, SchemaRef, SchemaConditional, SchemaDocument.
Add `$defs` to SchemaDocument.

**References to re-read BEFORE starting:**
- Old `draupnir_old/structures.py` — the Schema* models
- §5 "$defs naming" — path-based $defs keys
- §9 "Schema output models" — what carries over

**Gate 3 — Output model check:**
- [ ] SchemaDocument has `defs: dict[str, SchemaObject] | None`
- [ ] SchemaRef has `ref: str = Field(alias="$ref")`
- [ ] All output models support `model_dump_json(by_alias=True, exclude_none=True)`
- [ ] No behavioral changes from old output models (same JSON shape)
- [ ] `uv run pytest tests/test_guardrails.py` passes

---

### Phase 4: Loader

**Build:** `functions/impure/loader.py` — `load()` function,
`load_all_levels()` for supply-driven loading.

**References to re-read BEFORE starting:**
- §7 "The load function" — exact implementation
- §7 "Load strategy: supply-driven, full tree" — LEVEL_ORDER, phase order
- §6 "Pipeline: before and after" — Phase A is LOAD

**Tests:**
- load() single pattern from YAML → Pattern model in cache
- load() atom → Atom holding cached Pattern
- load_all_levels() populates cache in correct order
- Missing file → clear error
- Bad YAML shape → ValidationError

**Gate 4 — Loading discipline check:**
- [ ] `load()` is the ONLY function that calls `yaml.safe_load()`
- [ ] `load()` is the ONLY function that calls `Path.read_text()`
- [ ] Cache key is `"level/name"` (e.g., `"atom/kebab_string"`)
- [ ] `load_all_levels()` iterates LEVEL_ORDER exactly
- [ ] After loading, cache values are frozen Pydantic models holding models
- [ ] No demand-driven recursive loading (refs resolved from pre-filled cache)
- [ ] `load()` and `load_all_levels()` live in `functions/impure/`
- [ ] No IO anywhere else
- [ ] `uv run pytest tests/test_guardrails.py` passes

---

### Phase 5: Builder

**Build:** `functions/pure/builder.py` — `export_schema()`,
`export_all_schemas()`, `collect_shared_nodes()`, level-dispatched
`build_*` functions.

**References to re-read BEFORE starting:**
- §7 "Export: mechanical assembly" — the export algorithm
- §5 "$defs as Central Architecture" — detection, naming, wiring
- §4 "Level names as processing dispatch" — what each level maps to
- Old `draupnir_old/functions/pure/builders.py` — for output shape reference

**The builder converts loaded Pydantic models → JSON Schema output models.**
Level dispatch:
- Pattern → `{pattern: "..."}` or `{not: {pattern: "..."}}`
- Atom → `{type: "string", pattern: "..."}` (or integer/boolean)
- Enum → `{enum: [...]}`
- Element → inherits from atom/enum + format keyword
- Union → `{oneOf: [...]}`
- Tuple_ → `{type: "array", prefixItems: [...], items: false}`
- Simplearray → `{type: "array", items: {...}}`
- Simplegroup → `{type: "object", properties: {...}, required: [...]}`
- Group → `{type: "object", properties: {...}, required: [...]}`
- Array → `{type: "array", items: {type: "object", ...}}`
- Section → `{type: "object", properties: {...}, required: [...]}`
- Schema → SchemaDocument with $defs, $ref wiring

**Tests:**
- build_pattern → correct regex field
- build_atom → type + pattern combined
- build_union → oneOf with resolved members
- build_simplegroup → object with properties, correct required array
- build_group → nested object with field + container properties
- export_schema → complete SchemaDocument with $defs
- Shared nodes appear once in $defs, subsequent refs are $ref pointers

**Gate 5 — Builder discipline check:**
- [ ] Builder is in `functions/pure/` — NO file reads, NO writes
- [ ] Builder receives cache (dict[str, BaseModel]) as input
- [ ] Builder returns SchemaDocument, not dict
- [ ] $defs keys follow `level__name` pattern
- [ ] $ref pointers are `#/$defs/level__name`
- [ ] Shared node detection uses cache path identity
- [ ] Each build_* function < 50 lines
- [ ] model_dump_json() is NOT called in builder (that's the writer's job)
- [ ] `uv run pytest tests/test_guardrails.py` passes

---

### Phase 6: Writer + Pipeline + CLI

**Build:** `functions/impure/writer.py` (serialize, write, sidecar),
`functions/impure/pipeline.py` (run_all, run_check, run_list),
`cli.py` (argparse entry point).

**References to re-read BEFORE starting:**
- §9 "Shell & CLI Design" — CLI interface, pipeline orchestration
- §9 "Check mode" — drift detection
- Old `draupnir_old/functions/impure/writers.py` — serialize/write pattern
- Old `draupnir_old/cli.py` — argparse pattern (simplified)

**Tests:**
- serialize_schema → valid JSON string
- run_all → writes all schema files + sidecars
- run_check → detects drift correctly

**Gate 6 — Shell check:**
- [ ] `--all` is default (no schema name required)
- [ ] `model_dump_json(by_alias=True, exclude_none=True)` only in writer
- [ ] Pipeline: load_all_levels → export_all_schemas → write loop
- [ ] No per-schema loading (load once, export many)
- [ ] Verdandi root resolved to `tools/verdandi/` not `standards/toolcompose/`
- [ ] `uv run pytest tests/test_guardrails.py` passes

---

### Phase 7: Integration + Propagation

**Action:**
1. Run `draupnir --all` — generate all 12+ schemas
2. Compare output to old schemas — same structure, same fields
3. Run `draupnir --check` — verify no drift
4. Run downstream: `deploy_nornir_validators.py` (if applicable)
5. Run downstream: `generate_structures.py` (if applicable)
6. Run `scaffold_definition.py` — verify output handles $ref
7. Run `inspect_schema.py` — verify HTML output handles $ref
8. Run `uv run pytest` in all affected projects

**Gate 7 — Output compatibility check:**
- [ ] Every schema JSON has same top-level structure as old output
- [ ] Schema validates with `jsonschema` library
- [ ] `inspect_schema.py` produces valid HTML
- [ ] `scaffold_definition.py` produces valid output
- [ ] No `Parameter1` or duplicate classes from datamodel-codegen
- [ ] $defs section present where shared nodes exist
- [ ] $ref pointers resolve correctly
- [ ] `uv run pytest tests/test_guardrails.py` passes
- [ ] `uv run pytest` passes (full test suite)

---

### Phase 8: Cleanup

**Action:**
1. Delete `src/draupnir_old/` after all tests pass
2. Update `tools/draupnir/CLAUDE.md` for new architecture
3. Delete any toolcompose references in remaining documentation

**Gate 8 — Clean state:**
- [ ] `src/draupnir_old/` deleted
- [ ] No imports from `draupnir_old` anywhere
- [ ] CLAUDE.md reflects new architecture
- [ ] All tests pass
- [ ] `draupnir --check` exits 0
- [ ] `uv run pytest tests/test_guardrails.py` passes (final confirmation)

---

## 12. Anti-Pattern Watchlist

These are the specific failure modes that post-compaction Claude will
be tempted toward. Each maps to an architecture violation.

| Temptation | Why it's wrong | What to do instead |
|-----------|---------------|-------------------|
| Create a "resolve" function | There is no resolution. Loading IS the pipeline. | Use BeforeValidator to convert refs during model_validate() |
| Create "Raw" models + "Resolved" models | One model per level, always in final form | Models hold models, not strings |
| Put YAML loading in resolver/builder | IO lives in `functions/impure/loader.py` ONLY | Loader fills cache, builder reads cache |
| Use AfterValidator for refs | Wrong order — type union check needs actual models | BeforeValidator converts string → model FIRST |
| Return dict from builder | model_dump_json() only at writer boundary | Return SchemaDocument from builder |
| Add methods to models | Frozen models, zero methods | Logic in `functions/pure/` |
| Write demand-driven recursive loader | Supply-driven: glob levels in order | `for level in LEVEL_ORDER: load_all(level)` |
| Keep old pipeline.py | Old shell is toolcompose-coupled | Fresh pipeline: load_all → export_all → write_all |
| Create per-schema loading | Load once, export many | load_all_levels() fills cache, export_all_schemas() reads it |
| Put hierarchy checks in separate validator | Type unions ARE the hierarchy check | FieldRef = Pattern \| Atom \| Enum \| Element \| Union |
| Create 800-line structures.py | Split by tier into structures/ | structures/fields.py, structures/simple_containers.py, etc. |
| Skip gate checks | "I know what I'm doing" | You don't after compaction. Re-read the section. |
