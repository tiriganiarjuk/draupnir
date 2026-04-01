# Why We Keep Getting Stuck

## The Pattern

Every attempt to fix the Callable DI problem has followed the same arc:

1. Identify the violation (28 `no_callable_params` across 12 files)
2. Trace the root cause (`build_fn: Callable` threading recursive dispatch through every builder)
3. Propose a solution that preserves the recursive structure (BuildContext, bottom-up with lookup, etc.)
4. Hit zone/level/import violations in the new solution
5. Add more workarounds to satisfy constraints
6. Realize the workarounds create new violations
7. Start over

This has happened **three times** in this session alone:

### Attempt 1: BuildContext dataclass

Move `build_model` and `build_or_ref` to `transform/schema_build/dispatch.py` with a `BuildContext` dataclass. All builders receive context instead of Callable.

**Why it failed:** 17 gleipnir violations immediately:
- `impure_module_quarantine`: Transform importing from impure (cache_key_to_defs_key)
- `v2_import_boundaries`: Transform cannot import impure
- `v2_classes_only_in_structure`: Class defined outside structure zone
- `pydantic_only`: @dataclass instead of BaseModel
- `v2_dispatch_only_tables`: Non-dispatch code in dispatch file
- `no_future_annotations`: PEP 563 import

The fundamental problem: `build_model` dispatches to builders in transform, and builders call back to `build_or_ref` for recursion. This creates a circular dependency between orchestrate and transform that **cannot be expressed as static imports**.

### Attempt 2: Bottom-up with `built` dict

Build in dependency order, look up pre-built children from `built: dict[int, BaseModel]`. No recursion needed.

**Progress:** Successfully converted zone_collect, schema_build/primitive, simple, assembled to use `built` dict. But then:

**Where it stalled:** The `$defs` deduplication still needed to happen somewhere. The plan was "orchestrate loop replaces shared entries with SchemaRef after building." This works mechanically but required:
- A `build_order` function (topological sort of model instances)
- A `lookup` function that handles the $ref substitution
- Expanding the dispatch table from 5 to 14 types
- Rewriting `export_schema` and `export_fragment`
- Moving `cache_key_to_defs_key` between zones

Each of these changes was individually reasonable but together they represented a massive rewrite with many moving parts — and I was coding reactively without a clear picture of the whole.

### Attempt 3: Ref type aliases with `| str`

Add `| str` to all ref type aliases so `model_validate_json` accepts string refs from the gate output.

**Why it was catastrophic:** The ref type aliases are shared between input loading and output schema generation. Adding `| str` poisoned the output schemas — every downstream nornir gate would validate against wrong schemas. The entire pipeline from nornir gates through regin to galdr was contaminated.

## The Root Cause

**We kept trying to fix the symptom (Callable DI) while preserving the disease (recursive dispatch).**

The recursive tree-walk pattern is the architectural problem. It requires some mechanism for builders to call back into the dispatcher. That mechanism can be:
- A Callable parameter (current: violates `no_callable_params`)
- A static import (impossible: creates circular dependency between orchestrate and transform)
- A context object carrying a dispatch function (same as Callable with extra steps)
- A lookup dict with post-hoc $ref substitution (works but requires a separate `build_order` function and complex orchestration)

All of these are workarounds for the same underlying issue: **recursive descent requires the leaf to know how to call the root.** That's an upward dependency, and the architecture correctly forbids it.

## The Correct Diagnosis

The guardrails were not obstacles to work around. They were **diagnostic signal**:

> "If you can't solve the problem while staying within the structure and guardrails, you haven't found the right architecture yet."

The Callable violations, the zone boundary violations, the circular import attempts — all of them were saying the same thing: **recursion doesn't fit this architecture.** Not because the architecture is wrong, but because the problem doesn't require recursion.

Schemas are a topological problem. The data is a directed acyclic graph. The solution is a graph — not a recursive tree walk.

## What the Right Solution Looks Like

See `WHY_NETWORK_GRAPHS_ARE_THE_SOLUTION.md`.

## Cleanup Performed (2026-04-01)

The dead recursive code has been removed to prevent future sessions from being misled by its existence. Even if you know the code is wrong, its presence pulls you toward it — training data gravity. Deleted:

### Full directories removed
- `logic/transform/ref_resolve/` — dict-walking `resolve_refs` (graph eliminates this)
- `logic/pure/tree_walk/` — `reverse_cache_index`, `count_refs`, `shared_keys`, `iter_child_models`, `wrap_array_as_object` (graph in-degree and topological sort replace all of this)

### Files removed
- `logic/impure/loader/assembled.py` — yaml.safe_load + resolve_refs + model_validate pipeline
- `logic/impure/loader/composed.py` — level-ordered iteration with Callable DI
- `logic/transform/schema_build/composed.py` — recursive dispatch (`build_field`, `build_simple`, `build_verdandi_field`, `build_schema_properties`)
- `logic/transform/field_annotate/assembled.py` — Callable-based `build_verdandi_field_refs`

### Gutted
- `logic/orchestrate/compile/orchestrate.py` — deleted `build_or_ref`, `build_model`, `resolve_handler`, `resolve_container_handler`, `export_schema`, `export_fragment`, `export_all_schemas`. Pipeline modes are stubs. CLI routing intact.

### What survived (graph-compatible)
- `schema_build/simple.py`, `assembled.py`, `primitive.py` — all use `built: dict[int, BaseModel]`
- `zone_collect/` — fully converted to `built` dict
- `conditional_build/` — pure, no old-pattern dependencies
- `field_annotate/simple.py`, `composed.py` — pure metadata
- `loader/ffi.py`, `loader/primitive.py` — gate + path helpers
- `orchestrate/compile/dispatch.py` — type→builder routing table
- All structure models, config, writer, pipeline utils

Zero `yaml` imports remain in the codebase.
