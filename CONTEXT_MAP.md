<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!-- DO NOT EDIT THIS BLOCK. Before editing ANY part of this file, you MUST  -->
<!-- first read /Users/johnny/ai/CONTEXT_MANAGEMENT_SYSTEM.md — it defines  -->
<!-- what this file is for and what may NOT go in it.                        -->
<!--                                                                          -->
<!-- This file is a MAP (a router), not a source. Its only job is to tell    -->
<!-- you WHERE the context lives — it never holds the context, state, or     -->
<!-- progress itself. Reading this map does NOT orient you; you are NOT      -->
<!-- oriented until you have read the Orientation-gate docs it points to, in -->
<!-- the order given.                                                         -->
<!--                                                                          -->
<!-- THE WHITELIST RULE: if a doc is not in this map, it is not for           -->
<!-- orientation — do not read it. A stale doc is UNLINKED or DELETED, never -->
<!-- flagged in place. No freshness tags. No "do-not" guards. No state.       -->
<!-- Behavioral rules live in CLAUDE.md, not here.                            -->
<!--                                                                          -->
<!-- This file is LOW-CHURN. It changes only when how-to-get-oriented        -->
<!-- changes — i.e. a doc is added or removed. It is not a worklog and is    -->
<!-- not regenerated per session.                                            -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->

# CONTEXT_MAP — Draupnir

## Purpose

The schema compiler: it turns the Verdandi YAML hierarchy into JSON Schema documents, reliably and idempotently, and is the enforcement half of Verdandi's constraints.

---

## Orientation gate — read these, in this order, to be oriented

1. `~/ai/smidja/galdr/context/AGENT_BUILD_SYSTEM.md` — why the pipeline exists at all: determinism as the goal, the double gate, and the difference between build-time and run-time flows. Reading the five-part chain as one runtime pipeline is a common and costly mistake this document exists to prevent.
2. `~/ai/smidja/galdr/context/DRAUPNIR_ELEMENT.md` — Draupnir's own reason for being: why compilation is a graph walk with zero recursion, what the self-hosting loop closes, why fragments exist, and the one gap that is load-bearing.
3. `~/ai/smidja/galdr/context/VERDANDI_ELEMENT.md` — the input. You cannot reason about the compiler without knowing what the hierarchy is for and why an LLM must not author a schema directly.

> The next four are read by you, personally, in this context — never delegated to a
> subagent, never absorbed via a summary.

4. `WHY_THIS_FEELS_WRONG.md` — the frame: what this environment is, and why it will feel over-constrained until you understand it.
5. `EVERY_CHECK_IS_A_PROXY.md` — why the feedback steers where it steers. Read before the next one, so the level system reads as engineering rather than as limits.
6. `THE_LEVEL_SYSTEM.md` — zones, levels, and the decision procedure for where every piece of code lives. Prerequisite to writing anything.
7. `HOW_DATA_ENTERS.md` — the boundary: how external data becomes typed, and why unknown data never gets in.

**Proof:** before writing anything, state (a) why recursive descent was abandoned here and what the three attempts to rescue it have in common, (b) what the self-hosting loop makes impossible, and (c) one thing you would have written that this architecture forbids. If you cannot, you are not oriented — go back and read.

---

## Refresh guide — want X → read Y

| Need | Read |
|------|------|
| deep architectural rationale, model definitions, export strategy | `DRAUPNIR_REDESIGN.md` |
| where a function goes / what zone / what level | `THE_LEVEL_SYSTEM.md` |
| how external data becomes typed / a shape has no model | `HOW_DATA_ENTERS.md` |
| how to run it / what the flags are | `src/draupnir/cli.py` — the CLI is the truth. There is no `--all`; bare `uv run draupnir` is generate-everything |
| what the input hierarchy allows | `~/ai/smidja/verdandi/COMPOSITION_RULES.md` |
| what the output is embedded into | `context/NORNIR_GATES_ELEMENT.md` |
| what a generated schema looks like | `~/ai/smidja/verdandi/{project}/output/*.schema.json` |
| whether a generated schema drifted | `uv run draupnir --check` — compiles in memory, reports without writing |
| the full forward cascade after an edit | `context/AGENT_BUILD_SYSTEM.md` § The forward cascade |
| current state / what's left to build | read live — the code and `git log`. Nothing is stored |
