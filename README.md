# Draupnir

Schema generator for the agent definition pipeline. Reads a typed composition hierarchy and compiles it into JSON Schema documents using directed graph traversal — no recursion.

**Part of the agent definition pipeline:** [Verdandi](https://github.com/johnny111272/verdandi) → Draupnir → [Nornir](https://github.com/johnny111272/nornir) Gates → [Regin](https://github.com/johnny111272/regin) → Galdr

## What This Is

Draupnir reads a composition hierarchy defined in Verdandi (YAML files across 15 levels, one project at a time) and produces that project's JSON Schema documents: its top-level schemas, plus standalone schemas for the include fragments a definition may pull in.

The generated schemas become the enforcement layer for the entire pipeline. Nornir's compiled gate modules embed these schemas at compile time for stage-boundary validation. Regin's Pydantic models are generated from these schemas. The schemas are the contract between every stage.

## The Graph Approach

The central architectural decision in Draupnir is treating schema compilation as a graph problem rather than a tree-walking problem.

The YAML files reference each other through string cache keys, forming a directed acyclic graph. The LLM coding assistant repeatedly attempted to solve this with complex recursive traversals — threading callable parameters through every builder, maintaining reverse indices, counting references through tree walks. The recursion kept fighting the architecture because it was encoding a graph problem into a tree-walk pattern.

The solution was to recognise what the data actually is: a network graph. Draupnir builds a NetworkX directed graph where nodes are type definitions and edges are references. Once the graph exists, every operation that recursion struggled with becomes an intrinsic graph property:

- **Build order** is a topological sort — children before parents, computed once
- **Deduplication** ($defs) is an in-degree query — nodes referenced by two or more parents go into shared definitions
- **Subtree extraction** is `nx.descendants` — filter the global sort to just what a particular schema needs
- **Type dispatch** is a node attribute lookup — each node carries its model type, a dispatch table maps type to builder

The entire compilation is a linear walk over the topologically sorted graph. Zero recursion anywhere. The graph is the single source of truth for all parent-child relationships, zone annotations, and conditional dependencies.

## Key Concepts

**Supply-driven loading.** Levels load in declaration order (pattern first, schema last), so every reference a file names is already loaded when the file validates. A reference stays the string it was authored as: it is the cache key, and it becomes an edge in the graph. Every model is in final form from the moment it validates. Loading is the pipeline.

**Typed at the door.** Draupnir imports no YAML parser. A compiled Nornir reader reads each file, validates it against its level's schema, and returns either the validated JSON or a refusal carrying its failure class. A refusal stops the run.

**The self-hosting loop.** The models that define what a Verdandi file may contain are exported as the input schemas the reader validates against, and the input models that parse the reader's output are generated from those same schemas. One definition, two consumers.

**Pure/impure boundary.** I/O lives in the impure zone: the reader wrappers on the way in, the writer on the way out. The graph build, traversal, and schema compilation are entirely pure.

**Zone-aware edges.** Edges carry metadata about their zone context (required, optional, conditional) and when-conditions. This means the graph encodes not just what references what, but the semantic relationship — whether a reference is mandatory, optional, or conditionally present based on other field values.

## Usage

```bash
uv run draupnir                    # Generate every project's schemas and fragments
uv run draupnir --project <name>   # Generate one project
uv run draupnir --check            # Report drift without writing
```

After regenerating schemas, rebuild downstream:

```bash
cd ../nornir && nornir_deploy --build gates    # Recompile gate modules
cd ../regin && uv run python src/regin/generate_structures.py  # Regenerate Pydantic models
```

## Licence

Copyright (c) 2025–2026 John Oker-Blom

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

See [LICENSE](LICENSE) for the full licence text.
