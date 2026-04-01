# Why Network Graphs Are the Solution

## The Problem, Restated

Draupnir loads ~348 Verdandi YAML files into a cache of Pydantic models. Each file may reference other files via string cache keys (e.g., `"atom/str"`, `"simplegroup/context_item_raw"`). After loading, the models form a directed acyclic graph — and draupnir needs to compile this into JSON Schema documents.

The compilation requires three things:
1. **Build order** — children before parents (topological sort)
2. **Deduplication** — models referenced by 2+ parents go into `$defs` (in-degree >= 2)
3. **Type dispatch** — each model type has a specific builder function

The current recursive approach conflates all three into a single `build_fn: Callable` that threads through every builder. This creates the Callable DI problem.

## Why a Graph Solves All Three

A directed graph where **nodes are model instances** and **edges are references** gives all three requirements as intrinsic properties:

### 1. Build order = topological sort

The graph's topological sort IS the build order. No separate `build_order` function needed. No `reverse_cache_index` → `count_refs` → `shared_keys` pipeline. The sort falls directly out of the graph structure.

### 2. Deduplication = in-degree

A node with in-degree >= 2 is referenced by multiple parents. It belongs in `$defs`. A node with in-degree 1 is inlined. The graph already knows this — no tree walk to count refs, no `shared` frozenset. Just ask the graph.

### 3. Type dispatch = node attribute

Each node carries its model type. The dispatch table maps type → builder. The graph walk applies the right builder to each node in topological order. No recursive dispatch, no runtime `isinstance` chains.

## Where the Graph Comes From

**The loader already builds the graph.** Every string ref in every YAML file is an edge. The cache keys are the node identifiers. The resolution step (currently `resolve_refs` walking a dict to replace strings with model instances) is literally traversing the edge list.

Instead of resolving refs by mutating dicts, the loader can register edges in a graph. When loading is complete, the graph is complete.

With the gate architecture:
1. Gate reads file → validates → returns JSON string
2. `model_validate_json` → input model with string refs (ref fields typed as `str`)
3. Each string ref is a graph edge: `(parent_cache_key, child_cache_key)`
4. After all files loaded → graph is complete → topological sort → build order → compile

The string refs are not a problem to resolve. They ARE the graph edges. The input models with `str` ref fields are the graph's raw data, not a deficiency that needs "resolution."

## What the Graph Replaces

| Current | Graph approach |
|---------|---------------|
| `reverse_cache_index(cache)` | Graph node lookup |
| `count_refs(root, reverse)` | In-degree query |
| `shared_keys(counts)` | Filter: in-degree >= 2 |
| `build_order(root)` | Topological sort |
| `resolve_refs(data, cache)` | Not needed — refs are edges |
| `build_fn: Callable` threading | Not needed — linear walk |
| `build_or_ref` $defs decision | In-degree check at build time |
| `build_model` recursive dispatch | Dispatch table + linear walk |

The entire `pure/tree_walk/` zone and the Callable DI pattern become unnecessary. The `transform/ref_resolve/` zone becomes unnecessary. Resolution, counting, ordering, and deduplication all collapse into graph operations.

## The Key Insight

**Schemas are a topological problem.**

A JSON Schema is a description of a data shape. When that shape has shared components ($defs), the schema is encoding a graph — nodes are type definitions, edges are references ($ref). The compiler's job is to take the input graph (Verdandi models) and produce the output graph (JSON Schema with $defs).

Graph in → graph out. Using a graph as the intermediate representation is not an optimization — it's the natural representation. Recursion was an artificial encoding of a graph problem into a tree-walk pattern, and that's why it kept fighting the architecture.

## Input Models: Generated, Not Hand-Written (2026-04-01 update)

The previous attempt to create input models by adding `| str` to existing ref type aliases poisoned the entire pipeline. The correct approach: **generate input models from the same schemas the gate uses.**

### The Pattern (same as Regin)

Regin already generates Pydantic models from Draupnir's output schemas using `datamodel-code-generator` + post-processing. We reuse this exact pattern within Draupnir itself:

```
Original Verdandi models (hand-written, with model type refs)
  → model_json_schema() + ref-to-string transform (export_input_schemas.py already does this)
    → input schemas (15 JSON Schema files — already exist in schemas/input/)
      → datamodel-code-generator + Regin-style post-processing
        → generated input models (structure/gen/, with str ref fields)
```

**One source of truth** (original models) → **two consumers** (gate validation + generated input models) → **zero manual sync**.

### Why This Works

- Original models never change — no `| str` pollution
- Generated models are always in sync with gate schemas (same source)
- Change cascade is automated: change original model → re-export schemas → re-generate input models
- The `built` dict keys become cache key strings (`built["atom/str"]`) instead of opaque `id()` integers
- Regin's post-processing solves known `datamodel-code-generator` issues: `__future__` annotations breaking Pydantic, duplicate constraints on RootModel refs

### Regin Reference

The model generation system to study is at:
- **Script:** `regin/src/regin/generate_structures.py`
- **Config:** `regin/src/regin/codegen_schemas.toml`
- **Post-processing:** `regin/src/regin/logic/transform/codegen_clean/` (primitive.py, simple.py, composed.py)

Key flags: `--use-title-as-name`, `--use-standard-collections`, `--use-annotated`, `--input-file-type jsonschema`

## Implementation Implications

The graph approach means:
- **Input models** are generated from input schemas — `str` ref fields, guaranteed gate-compatible
- **The loader** calls the gate (reads file, validates, returns JSON), then `model_validate_json` with generated input models
- **The graph** is built from the cache — each entry is a node, each string ref field value is an edge
- **The compiler** walks the graph in topological order, builds JSON Schema for each node
- **$defs** decisions are automatic (in-degree >= 2)
- **No Callable parameters anywhere** — all builders receive pre-built children via `built` dict
- **No recursion anywhere** — linear walk in topological order
- **Zone boundaries respected naturally** — no upward dependencies needed

The gate, generated input models, graph, and linear compilation all fit the three-tier architecture without workarounds.

## What Was Removed (2026-04-01)

The old recursive code has been deleted to prevent it from misleading future sessions. See `WHY_WE_KEEP_GETTING_STUCK.md` for the full list. Key point: zero `yaml` imports remain, zero recursive dispatch functions remain. The codebase is clean for the graph approach.
