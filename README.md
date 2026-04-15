# Draupnir

Schema generator for the agent definition pipeline. Reads Verdandi's type hierarchy and produces JSON Schema documents.

**Part of the agent definition pipeline:** [Verdandi](https://github.com/johnny111272/verdandi) → Draupnir → [Nornir](https://github.com/johnny111272/nornir) Gates → [Regin](https://github.com/johnny111272/regin) → Galdr

## What This Is

Draupnir reads the composition hierarchy defined in Verdandi (~350 YAML files across 15 levels) and produces JSON Schema documents — 13 pipeline-stage schemas plus 7 include-fragment schemas — along with HTML sidecar visualisations.

The generated schemas become the enforcement layer for the entire pipeline. Nornir's compiled gate modules embed these schemas at compile time for stage-boundary validation. Regin's Pydantic models are generated from these schemas. The schemas are the contract between every stage.

## Key Concepts

**Supply-driven loading.** Levels load in declaration order (pattern first, schema last). Reference fields are resolved during model validation via Pydantic BeforeValidators. Every model is in final form from the moment it validates — there is no separate resolution step. Loading is the pipeline.

**Pure/impure boundary.** I/O exists in exactly two files: `loader.py` (reads) and `writer.py` (writes). Everything else is pure computation.

## Usage

```bash
uv run draupnir --all                  # Generate all schemas
uv run draupnir --project <name>       # Generate schemas for a single project
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
