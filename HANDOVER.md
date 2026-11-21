# HANDOVER — Draupnir, branch `typed-references`

Written at the end of one session for the next. Every line is a pointer, not a fact:
open the commit or file it names before acting on it. Orient through CONTEXT_MAP's
gate first, as always. Delete this file once its items are absorbed or done.

---

## Where things stand (verify with `git log master..typed-references`)

- **Paths located once.** `logic/impure/paths_locate/` builds `DraupnirPaths`; every entry
  point passes it down. Schema names live in `structure/config/draupnir_schemas.py`.
- **Sweep before load.** Each target lists `{project}/source` through
  `read_directory_links_followed_json` (new Nornir reader; follows the level links into
  core), sorts files into Verdandi files and strays (`pure/source_files/`), builds a
  `VerdandiManifest` (`transform/manifest_build/`), and the loader reads exactly those files.
- **Codegen targets computed.** `draupnir-generate-models` walks `Level` and
  `NornirToolSchema` (`structure/config/model_codegen.py`, `pure/model_locate/`).
  `tools/codegen_input.toml` is gone.
- **The flip.** `schemas/input/{level}.schema.json` are the AUTHORED SOURCE. Every object
  is closed; every reference def carries a level pattern `^(atom|enum|…)/<name>$`;
  simplegroup, group and shallowsection roots carry `minProperties: 3` (= at least one zone,
  explained in a `$comment`). The hand-written level models are removed; `Level`
  (`structure/config/levels.py`) maps to the generated models in `structure/gen/input/`.
- **Container limit.** A shallowsection naming more than 3 containers stops the run
  (`pure/composition_check/`, limit in `structure/config/composition_limits.py`).
- **Proof at last commit:** `uv run draupnir --check` exits 0 on both projects;
  `draupnir-generate-models` 18/18.

Other repos touched: Verdandi `typed-references` (COMPOSITION_RULES matched to the
implementation), Galdr `composition-engine` (DRAUPNIR_ELEMENT), `~/ai/control` `master`
(`library/systems/draupnir.xml`).

## Uncommitted on purpose

- `NornirToolSchema.directory_write_request` / `directory_write_report` and their generated
  models in `structure/gen/tools/` — groundwork for step 1 below.
- Timestamp-only diff in `structure/gen/tools/directory_listing.py`.

## Do not

- Run `draupnir-export-schemas` expecting level schemas — it now writes only
  `schemas/config/verdandi-manifest.schema.json`. The level schemas are edited by hand.
- Decompose to hit a CC band. Decompose by what a function does; when `v2_cc_level`
  fires, ask what the shape is telling you.

## Next, in order (agreed with the user)

1. **Per-project narrowing.** After the sweep, write `schemas/input/{project}/` with
   `write_json_validate_directory` (schema_dir = `schemas/config/`): `manifest.json` plus the
   15 level schemas, each reference pattern narrowed to an `enum` of that project's swept
   `level/name` keys at the pattern's levels. The loader then validates against the project
   directory. Written in every mode, `--check` included (agreed: it is an input to reading,
   not output). Read the levels from the source schemas' patterns — never reconstruct them.
2. **Nullable-wrapper cleanup** in the source schemas (`anyOf [X, {"type":"null"}]` with
   `default: null`). Clears the standing `v2_cc_level` on `shallowsection_container_count`.
3. **Problem 1:** name the loaded-node union, removing `dict[str, BaseModel]` / `BaseModel`
   signatures through loader, graph build and builders.
4. **Problem 2:** slim `logic/orchestrate/compile/orchestrate.py` (string literals,
   same-file calls, real work living in orchestrate).
5. **Flip `VerdandiManifest`** the same way: schema as source, model generated.
6. **Mandatory elements** (COMPOSITION_RULES item 3) — enforced nowhere.
7. **Small:** add `--disable-timestamp` to codegen; basedpyright finds no environment
   (`UV_PROJECT_ENVIRONMENT` is on the Derived volume, it looks for `.venv/`); stale `.qa`
   sidecars beside removed modules; untracked `src/draupnir_old.zip`.
8. **Later, user's plan:** define the input schemas as a Verdandi project, compile them with
   Draupnir, require byte-identical output to `schemas/input/`, then lock the source (schg).

## Open questions for the user

- `v2_cc_level` in `transform/` flags CC-2/3 functions that THE_LEVEL_SYSTEM's 1–3 band
  allows — the checker's count or the documented band is off.
- The guardrail finding list from the start of this work (366 total) predates the flip;
  re-run `syn` for the current map before choosing what to clear.
